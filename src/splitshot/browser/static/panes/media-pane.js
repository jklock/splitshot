export function createMediaPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  activity = () => {},
  callApi = async () => null,
  pickPath = async () => "",
  fileName = (value) => String(value || ""),
  splitSeconds = (value) => String(value ?? ""),
  setStatus = () => {},
} = {}) {
  const mediaSectionExpansionKey = "splitshot.media.sectionExpanded";
  let mediaMutationPending = false;

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
    if (!stage || stage.id !== activeStageId()) return stage;
    const projectedPrimary = project().primary_video || {};
    const projectedAdded = Array.isArray(project().merge_sources) ? project().merge_sources : [];
    const primaryIdentityMatches = String(projectedPrimary.path || "") === String(stage.primary_media?.path || "");
    const addedIdentity = (items) => items
      .map((source) => `${source.id || ""}:${source?.asset?.path || source?.path || ""}`)
      .join("|");
    if (!primaryIdentityMatches || addedIdentity(projectedAdded) !== addedIdentity(stageAddedMedia(stage))) {
      return stage;
    }
    return {
      ...stage,
      primary_media: projectedPrimary,
      added_media: projectedAdded,
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

  async function runMediaMutation(action) {
    if (mediaMutationPending) {
      setStatus("Wait for the current media action to finish.");
      return null;
    }
    mediaMutationPending = true;
    render();
    try {
      return await action();
    } finally {
      mediaMutationPending = false;
      render();
    }
  }

  async function selectStageRequest(stageId) {
    const proj = project();
    if (!proj || !stageId) return false;
    if (stageId === activeStageId()) return true;
    activity("media.select-stage", { stageId });
    const result = await callApi("/api/project/select-stage", { active_stage_id: stageId });
    if (!result) return false;
    render();
    return true;
  }

  async function selectStage(stageId) {
    return runMediaMutation(() => selectStageRequest(stageId));
  }

  async function createStage() {
    return runMediaMutation(async () => {
      activity("media.create-stage");
      const result = await callApi("/api/project/stage/create", {});
      if (result) setStatus("Created new stage.");
      return result;
    });
  }

  async function renameStage(stageId, label) {
    const trimmed = String(label || "").trim();
    if (!stageId || !trimmed) return;
    return runMediaMutation(async () => {
      activity("media.rename-stage", { stageId, label: trimmed });
      const result = await callApi("/api/project/stage/update", { stage_id: stageId, label: trimmed });
      if (result) setStatus(`Renamed stage to "${trimmed}".`);
      return result;
    });
  }

  async function deleteStage(stageId) {
    if (!stageId) return;
    return runMediaMutation(async () => {
      activity("media.delete-stage", { stageId });
      const result = await callApi("/api/project/stage/delete", { stage_id: stageId });
      if (result) setStatus("Deleted stage.");
      return result;
    });
  }

  async function setGlobalSettingsPrimary(stageId, enabled) {
    if (!stageId) return;
    return runMediaMutation(async () => {
      activity("media.global-settings-primary", { stageId });
      const result = await callApi("/api/project/stage/global-settings-primary", {
        stage_id: stageId,
        enabled: Boolean(enabled),
      });
      if (result) setStatus(enabled ? "Set global settings primary." : "Cleared global settings primary.");
      return result;
    });
  }

  async function ignoreGlobalSettings(stageId, enabled) {
    if (!stageId) return;
    return runMediaMutation(async () => {
      activity("media.ignore-global-settings", { stageId });
      const result = await callApi("/api/project/stage/ignore-global-settings", {
        stage_id: stageId,
        enabled: Boolean(enabled),
      });
      if (result) {
        setStatus(enabled
          ? "This stage now uses project or app defaults."
          : "This stage now follows the global settings primary.");
      }
      return result;
    });
  }

  async function clearPrimary(stageId) {
    if (!stageId) return;
    return runMediaMutation(async () => {
      activity("media.clear-primary", { stageId });
      const result = await callApi("/api/project/stage/clear-primary", { stage_id: stageId });
      if (result) setStatus("Cleared primary media.");
      return result;
    });
  }

  async function removeAdded(stageId, sourceId) {
    if (!stageId || !sourceId) return;
    return runMediaMutation(async () => {
      activity("media.remove-added", { stageId, sourceId });
      const result = await callApi("/api/project/stage/remove-added", { stage_id: stageId, source_id: sourceId });
      if (result) setStatus("Removed secondary media.");
      return result;
    });
  }

  async function setPrimary(stageId, sourceId) {
    if (!stageId || !sourceId) return;
    return runMediaMutation(async () => {
      activity("media.set-primary", { stageId, sourceId });
      const result = await callApi("/api/project/stage/set-primary", { stage_id: stageId, source_id: sourceId });
      if (result) setStatus("Set as primary media.");
      return result;
    });
  }

  async function openPrimaryForStage(stageId) {
    if (!stageId || !hasOpenProject()) return;
    return runMediaMutation(async () => {
      if (!(await selectStageRequest(stageId))) return null;
      activity("media.import-primary", { stageId });
      const selectedPath = await pickPath("primary", null, null, mediaPickerDefaultRoot());
      if (!selectedPath) return null;
      const result = await callApi("/api/project/stage/import-primary", { stage_id: stageId, path: selectedPath });
      if (result) setStatus("Imported primary media.");
      return result;
    });
  }

  async function openAddMoreForStage(stageId) {
    if (!stageId || !hasOpenProject()) return;
    return runMediaMutation(async () => {
      if (!(await selectStageRequest(stageId))) return null;
      const stage = activeStage();
      if (!stage?.primary_media?.path) {
        setStatus("Add primary media before adding secondary media.");
        return null;
      }
      activity("media.import-added", { stageId });
      const selectedPath = await pickPath("primary", null, null, mediaPickerDefaultRoot());
      if (!selectedPath) return null;
      const result = await callApi("/api/project/stage/import-added", { stage_id: stageId, path: selectedPath });
      if (result) setStatus("Imported secondary media.");
      return result;
    });
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
            ? `<button class="btn-sm btn-secondary media-replace-primary-btn" type="button" data-stage-id="${stageId}" ${mediaMutationPending ? "disabled" : ""}>Replace</button>
               <button class="btn-sm btn-danger media-remove-file-btn" type="button" data-stage-id="${stageId}" data-source-id="primary" ${mediaMutationPending ? "disabled" : ""}>Clear</button>`
            : `<button class="btn-sm btn-secondary media-set-primary-btn" type="button" data-stage-id="${stageId}" data-source-id="${sourceId}" ${mediaMutationPending ? "disabled" : ""}>Set Primary</button>
               <button class="btn-sm btn-danger media-remove-file-btn" type="button" data-stage-id="${stageId}" data-source-id="${sourceId}" ${mediaMutationPending ? "disabled" : ""}>Remove</button>`}
        </div>
      </article>
    `;
  }

  function syncInventoryFileRow(pane, sourceId, source) {
    const row = [...pane.querySelectorAll(".media-asset-row")]
      .find((item) => item.dataset.sourceId === sourceId);
    if (!(row instanceof HTMLElement)) return;
    const asset = source?.asset || source || {};
    const activeName = source?.active_display_name || fileName(asset.path || "");
    const name = row.querySelector(".media-asset-copy > strong");
    const meta = row.querySelector(".media-asset-copy > small");
    if (name) name.textContent = activeName;
    if (meta) meta.textContent = activeAssetMeta(source);
  }

  function renderActiveStageSection(stage) {
    const isGlobalPrimary = Boolean(stage?.id && project()?.global_settings_stage_id === stage.id);
    const ignoresGlobal = Boolean(stage?.ignore_global_settings);
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
              <select id="media-active-stage-select" ${mediaMutationPending ? "disabled" : ""}>${stageOptions}</select>
            </label>
            <label>Stage Name
              <input id="media-active-stage-label" type="text" value="${htmlEscape(stage ? stageLabel(stage) : "")}" placeholder="Stage name" ${mediaMutationPending ? "disabled" : ""} />
            </label>
          </div>
          <div class="media-active-stage-actions media-pane-actions media-pane-actions-split">
            <button class="btn-sm media-add-stage-btn" type="button" ${mediaMutationPending ? "disabled" : ""}>Add Stage</button>
            <button class="btn-sm btn-primary media-save-stage-btn" type="button" ${stage && !mediaMutationPending ? "" : "disabled"}>Save Stage</button>
            <button class="btn-sm btn-danger media-delete-stage-btn" type="button" data-stage-id="${stage?.id || ""}" ${stages().length > 1 && !mediaMutationPending ? "" : "disabled"}>Delete Stage</button>
          </div>
          <div class="media-global-settings-actions">
            <label class="check-row media-global-setting-row">
              <input id="media-global-settings-primary" type="checkbox" ${isGlobalPrimary ? "checked" : ""} ${stage && !mediaMutationPending ? "" : "disabled"} />
              <span><strong>Global Settings Primary</strong><small>Apply this stage's presentation settings to queued stages.</small></span>
            </label>
            <label class="check-row media-global-setting-row">
              <input id="media-ignore-global-settings" type="checkbox" ${ignoresGlobal ? "checked" : ""} ${stage && !isGlobalPrimary && !mediaMutationPending ? "" : "disabled"} />
              <span><strong>Ignore Global Settings</strong><small>Use project or application defaults for this stage.</small></span>
            </label>
          </div>
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
          <strong>Primary Media</strong>
          <div class="section-header-actions">
            ${stage?.primary_media?.path
              ? ""
              : `<button class="btn-sm btn-primary media-section-action-btn media-add-primary-btn" type="button" data-stage-id="${stage?.id || ""}" ${mediaMutationPending ? "disabled" : ""}>Add Primary</button>`}
            <button class="pane-toggle media-section-toggle" type="button" data-media-section="primary" aria-label="${primaryExpanded ? "Collapse" : "Expand"} Primary Media">${primaryExpanded ? "v" : ">"}</button>
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
          <strong>Secondary Media</strong>
          <div class="section-header-actions">
            <button class="btn-sm btn-primary media-intake-btn media-section-action-btn media-add-more-btn" type="button" data-stage-id="${stage?.id || ""}" ${stage?.primary_media?.path && !mediaMutationPending ? "" : "disabled"}>Add Media</button>
            <button class="pane-toggle media-section-toggle" type="button" data-media-section="added" aria-label="${addedExpanded ? "Collapse" : "Expand"} Secondary Media">${addedExpanded ? "v" : ">"}</button>
          </div>
        </div>
        <div class="media-pane-section-body media-asset-stack"${addedExpanded ? "" : " hidden"}>
          ${added.length
            ? added.map((source) => renderInventoryFileRow(stage.id, source, false)).join("")
            : '<div class="empty-state">No secondary media.</div>'}
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
        return;
      }
      if (target.id === "media-global-settings-primary") {
        const stage = activeStage();
        if (stage) void setGlobalSettingsPrimary(stage.id, target.checked);
        return;
      }
      if (target.id === "media-ignore-global-settings") {
        const stage = activeStage();
        if (stage) void ignoreGlobalSettings(stage.id, target.checked);
      }
    };
    pane.oninput = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (target?.id !== "media-active-stage-label") return;
      const stage = activeStage();
      const nextLabel = String(target.value || "").trim();
      const saveButton = pane.querySelector(".media-save-stage-btn");
      if (saveButton) {
        saveButton.disabled = mediaMutationPending
          || !stage
          || !nextLabel
          || nextLabel === stageLabel(stage);
      }
    };
    pane.onkeydown = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (target?.id !== "media-active-stage-label" || event.key !== "Enter") return;
      event.preventDefault();
      const stage = activeStage();
      const nextLabel = String(target.value || "").trim();
      if (stage && nextLabel && nextLabel !== stageLabel(stage)) {
        void renameStage(stage.id, nextLabel);
      }
    };
  }

  function renderStructureKey(stage) {
    const primaryExpanded = sectionExpanded("primary");
    const addedExpanded = sectionExpanded("added");
    const added = stage ? stageAddedMedia(stage) : [];
    const primaryIdentity = stage?.primary_media?.path || "";
    const addedIdentity = added
      .map((source) => `${source.id || ""}:${source?.asset?.path || source?.path || ""}`)
      .join(",");
    return `${stage?.id || ""}|${stages().length}|${primaryIdentity}|${addedIdentity}|${primaryExpanded}|${addedExpanded}|${project()?.global_settings_stage_id || ""}|${Boolean(stage?.ignore_global_settings)}|${mediaMutationPending}`;
  }

  function syncScalarControls(pane, stage) {
    const count = stageAssetCount(stage);
    const statusText = pane.querySelector(".pane-status-text");
    if (statusText) statusText.textContent = `${count} asset${count === 1 ? "" : "s"}`;
    pane.setAttribute("aria-busy", mediaMutationPending ? "true" : "false");
    if (stage?.primary_media?.path) syncInventoryFileRow(pane, "primary", stage.primary_media);
    stageAddedMedia(stage).forEach((source) => {
      syncInventoryFileRow(pane, source.id || "", source);
    });

    const select = pane.querySelector("#media-active-stage-select");
    if (select && documentObject.activeElement !== select) {
      select.disabled = mediaMutationPending;
      const desiredValue = stage?.id || "";
      if (select.value !== desiredValue) {
        select.value = desiredValue;
      }
    }

    const labelInput = pane.querySelector("#media-active-stage-label");
    if (labelInput && documentObject.activeElement !== labelInput) {
      labelInput.disabled = mediaMutationPending;
      const desiredLabel = stage ? stageLabel(stage) : "";
      if (labelInput.value !== desiredLabel) {
        labelInput.value = desiredLabel;
      }
    }

    const saveBtn = pane.querySelector(".media-save-stage-btn");
    if (saveBtn) {
      const draft = String(labelInput?.value || "").trim();
      saveBtn.disabled = !stage
        || mediaMutationPending
        || !draft
        || draft === stageLabel(stage);
    }

    const deleteBtn = pane.querySelector(".media-delete-stage-btn");
    if (deleteBtn) {
      deleteBtn.disabled = stages().length <= 1 || mediaMutationPending;
      deleteBtn.dataset.stageId = stage?.id || "";
    }

    const addStageBtn = pane.querySelector(".media-add-stage-btn");
    if (addStageBtn) addStageBtn.disabled = mediaMutationPending;

    const globalPrimaryInput = pane.querySelector("#media-global-settings-primary");
    if (globalPrimaryInput) {
      const active = Boolean(stage?.id && project()?.global_settings_stage_id === stage.id);
      globalPrimaryInput.disabled = !stage || mediaMutationPending;
      globalPrimaryInput.checked = active;
    }
    const ignoreGlobalInput = pane.querySelector("#media-ignore-global-settings");
    if (ignoreGlobalInput) {
      const ignored = Boolean(stage?.ignore_global_settings);
      const active = Boolean(stage?.id && project()?.global_settings_stage_id === stage.id);
      ignoreGlobalInput.disabled = !stage || active || mediaMutationPending;
      ignoreGlobalInput.checked = ignored;
    }

    const addPrimaryBtn = pane.querySelector(".media-add-primary-btn");
    if (addPrimaryBtn) {
      addPrimaryBtn.disabled = mediaMutationPending;
      addPrimaryBtn.dataset.stageId = stage?.id || "";
    }

    const addMoreBtn = pane.querySelector(".media-add-more-btn");
    if (addMoreBtn) {
      addMoreBtn.disabled = !stage?.primary_media?.path || mediaMutationPending;
      addMoreBtn.dataset.stageId = stage?.id || "";
    }

    const primarySection = pane.querySelector("[data-media-section=\"primary\"]")?.closest(".media-pane-section");
    if (primarySection) {
      const body = primarySection.querySelector(".media-pane-section-body");
      const expanded = sectionExpanded("primary");
      primarySection.classList.toggle("collapsed", !expanded);
      if (body) body.hidden = !expanded;
    }

    const addedSection = pane.querySelector("[data-media-section=\"added\"]")?.closest(".media-pane-section");
    if (addedSection) {
      const body = addedSection.querySelector(".media-pane-section-body");
      const expanded = sectionExpanded("added");
      addedSection.classList.toggle("collapsed", !expanded);
      if (body) body.hidden = !expanded;
    }
  }

  function render() {
    const pane = $("media-pane");
    if (!pane) return;
    const stage = activeStage();
    const structureKey = renderStructureKey(stage);
    if (pane.dataset.renderStructureKey === structureKey && pane.querySelector(".media-pane-shell")) {
      syncScalarControls(pane, stage);
      return;
    }
    const count = stageAssetCount(stage);
    pane.setAttribute("aria-busy", mediaMutationPending ? "true" : "false");
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
    pane.dataset.renderStructureKey = structureKey;
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
