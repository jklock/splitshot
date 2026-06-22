export function createMediaPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  setActiveStageId = () => {},
  activity = () => {},
  callApi = async () => null,
  openPrimaryFileInput = () => {},
  openMediaAddMoreInput = () => {},
  fileName = (value) => String(value || ""),
  splitSeconds = (value) => String(value ?? ""),
  sendKeepaliveJson = () => false,
} = {}) {
  const stageExpansionKey = "splitshot.media.stageExpanded";
  const sectionExpansion = new Map([
    ["primary", true],
    ["added", true],
    ["stages", true],
  ]);

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

  function currentAssetCount() {
    return stageAssetCount(activeStage());
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

  function isStageExpanded(stageId) {
    try {
      const stored = JSON.parse(windowObject?.localStorage?.getItem(stageExpansionKey) || "{}");
      if (stored && typeof stored === "object" && stored[stageId] !== undefined) return Boolean(stored[stageId]);
    } catch (_) {}
    return false;
  }

  function setStageExpanded(stageId, expanded) {
    try {
      const stored = JSON.parse(windowObject?.localStorage?.getItem(stageExpansionKey) || "{}");
      const next = { ...(stored && typeof stored === "object" ? stored : {}), [stageId]: expanded };
      windowObject?.localStorage?.setItem(stageExpansionKey, JSON.stringify(next));
    } catch (_) {}
  }

  function toggleStage(stageId) {
    setStageExpanded(stageId, !isStageExpanded(stageId));
    render();
  }

  function isSectionExpanded(sectionId) {
    return sectionExpansion.get(sectionId) !== false;
  }

  function toggleSection(sectionId) {
    sectionExpansion.set(sectionId, !isSectionExpanded(sectionId));
    render();
  }

  function renderSectionHeader(title, sectionId, actions = "") {
    const expanded = isSectionExpanded(sectionId);
    return `
      <div class="section-header media-section-header">
        <strong>${title}</strong>
        <div class="section-header-actions">
          ${actions}
          <button class="scoring-shot-toggle" type="button" data-media-section-toggle="${sectionId}" aria-label="${expanded ? "Collapse" : "Expand"} ${title}">${expanded ? "\u25BC" : "\u25B6"}</button>
        </div>
      </div>
    `;
  }

  function selectStage(stageId, options = {}) {
    const edit = Boolean(options?.edit);
    const proj = project();
    if (!proj || !stageId) return;
    proj.active_stage_id = stageId;
    setActiveStageId(stageId);
    sendKeepaliveJson("/api/project/select-stage", { active_stage_id: stageId });
    activity(edit ? "media.edit-stage" : "media.select-stage", { stageId });
    render();
  }

  async function clearPrimary(stageId) {
    if (!stageId) return;
    activity("media.clear-primary", { stageId });
    await callApi("/api/project/stage/clear-primary", { stage_id: stageId });
  }

  async function removeAdded(stageId, sourceId) {
    if (!stageId || !sourceId) return;
    activity("media.remove-added", { stageId, sourceId });
    await callApi("/api/project/stage/remove-added", { stage_id: stageId, source_id: sourceId });
  }

  async function setPrimary(stageId, sourceId) {
    if (!stageId || !sourceId) return;
    activity("media.set-primary", { stageId, sourceId });
    await callApi("/api/project/stage/set-primary", { stage_id: stageId, source_id: sourceId });
  }

  function openPrimaryForStage(stageId) {
    if (!stageId || !hasOpenProject()) return;
    selectStage(stageId);
    activity("media.import-primary", { stageId });
    openPrimaryFileInput();
  }

  function openAddMoreForStage(stageId) {
    if (!stageId || !hasOpenProject()) return;
    selectStage(stageId);
    activity("media.import-added", { stageId });
    openMediaAddMoreInput();
  }

  function renderInventoryFileRow(stageId, source, index, isPrimary = false) {
    const asset = source.asset || source;
    const sourceId = isPrimary ? "primary" : (source.id || "");
    return `
      <article class="media-asset-row" data-stage-id="${stageId}" data-source-id="${sourceId}">
        <div class="media-asset-copy">
          <strong>${isPrimary ? "Primary" : `Added ${index + 1}`}</strong>
          <span>${fileName(asset.path || "")}</span>
          <small>${assetMeta(asset)}</small>
        </div>
        <div class="media-asset-actions">
          ${isPrimary
            ? '<span class="primary-badge">Primary</span>'
            : `<button class="btn-sm btn-secondary media-set-primary-btn" type="button" data-stage-id="${stageId}" data-source-id="${sourceId}">Set Primary</button>`}
          <button class="btn-sm btn-danger media-remove-file-btn" type="button" data-stage-id="${stageId}" data-source-id="${sourceId}">${isPrimary ? "Clear" : "Remove"}</button>
        </div>
      </article>
    `;
  }

  function renderPrimarySection(stage) {
    const primary = stage?.primary_media;
    const ready = hasOpenProject();
    return `
      <section class="settings-section media-pane-section ${isSectionExpanded("primary") ? "" : "collapsed"}" data-media-section="primary">
        ${renderSectionHeader(
          "Primary",
          "primary",
          `<button class="btn-sm btn-secondary media-replace-primary-btn" type="button" data-stage-id="${stage.id}" ${ready ? "" : "disabled"}>Replace</button>`,
        )}
        <div class="media-asset-stack">
          ${primary?.path
            ? renderInventoryFileRow(stage.id, { asset: primary, id: "primary" }, 0, true)
            : '<div class="empty-state">No primary asset.</div>'}
        </div>
      </section>
    `;
  }

  function renderAddedSection(stage) {
    const added = stageAddedMedia(stage);
    const ready = hasOpenProject();
    return `
      <section class="settings-section media-pane-section ${isSectionExpanded("added") ? "" : "collapsed"}" data-media-section="added">
        ${renderSectionHeader(
          "Added Media",
          "added",
          `<button class="btn-sm btn-secondary media-add-more-btn" type="button" data-stage-id="${stage.id}" ${ready ? "" : "disabled"}>Add More</button>`,
        )}
        <div class="media-asset-stack">
          ${added.length
            ? added.map((source, index) => renderInventoryFileRow(stage.id, source, index, false)).join("")
            : '<div class="empty-state">No added media.</div>'}
        </div>
      </section>
    `;
  }

  function renderStageNavigatorRow(stage) {
    const selected = stage.id === activeStageId();
    const expanded = isStageExpanded(stage.id);
    return `
      <article class="media-stage-nav-card ${selected ? "selected" : ""}" data-stage-nav-id="${stage.id}">
        <div class="media-stage-nav-header section-header-with-toggle">
          <div class="media-stage-nav-copy">
            <strong>${stageLabel(stage)}</strong>
            <small>${stageMeta(stage) || "No imported context"}</small>
          </div>
          <button class="scoring-shot-toggle media-stage-toggle" type="button" data-stage-id="${stage.id}" aria-label="${expanded ? "Collapse" : "Expand"} stage">${expanded ? "\u25BC" : "\u25B6"}</button>
        </div>
        <div class="media-stage-nav-body"${expanded ? "" : " hidden"}>
          <div class="media-stage-nav-actions">
            <button class="btn-sm btn-ghost media-select-stage-btn" type="button" data-stage-id="${stage.id}">${selected ? "Live Stage" : "Select"}</button>
            <button class="btn-sm btn-secondary media-edit-stage-btn" type="button" data-stage-id="${stage.id}">Edit Stage</button>
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
      const stageToggle = target.closest(".media-stage-toggle");
      if (stageToggle instanceof HTMLElement) {
        event.preventDefault();
        event.stopPropagation();
        toggleStage(stageToggle.dataset.stageId || "");
        return;
      }
      const sectionToggle = target.closest("[data-media-section-toggle]");
      if (sectionToggle instanceof HTMLElement) {
        event.preventDefault();
        event.stopPropagation();
        toggleSection(sectionToggle.dataset.mediaSectionToggle || "");
        return;
      }
      const editStageButton = target.closest(".media-edit-stage-btn");
      if (editStageButton instanceof HTMLElement) {
        selectStage(editStageButton.dataset.stageId || "", { edit: true });
        return;
      }
      const selectStageButton = target.closest(".media-select-stage-btn");
      if (selectStageButton instanceof HTMLElement) {
        selectStage(selectStageButton.dataset.stageId || "");
        return;
      }
      const replacePrimaryButton = target.closest(".media-replace-primary-btn");
      if (replacePrimaryButton instanceof HTMLElement) {
        openPrimaryForStage(replacePrimaryButton.dataset.stageId || "");
        return;
      }
      const addMoreButton = target.closest(".media-add-more-btn");
      if (addMoreButton instanceof HTMLElement) {
        openAddMoreForStage(addMoreButton.dataset.stageId || "");
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
      const stageCard = target.closest("[data-stage-nav-id]");
      if (stageCard instanceof HTMLElement) {
        selectStage(stageCard.dataset.stageNavId || "");
      }
    };
  }

  function render() {
    const pane = $("media-pane");
    if (!pane) return;
    const stage = activeStage();
    const count = currentAssetCount();
    pane.innerHTML = `
      <div class="pane-section media-pane-shell">
        <div class="section-header pane-title-row">
          <h3>Media</h3>
          <span class="pane-summary-token">${count} asset${count === 1 ? "" : "s"}</span>
        </div>
        ${stage
          ? `
            <div class="media-pane-active-stage">
              ${renderPrimarySection(stage)}
              ${renderAddedSection(stage)}
            </div>
            <section class="settings-section media-pane-section ${isSectionExpanded("stages") ? "" : "collapsed"}" data-media-section="stages">
              ${renderSectionHeader("Stages", "stages")}
              <div class="media-stage-nav-list">
                ${stages().map((item) => renderStageNavigatorRow(item)).join("")}
              </div>
            </section>
          `
          : '<div class="empty-state">No stages available.</div>'}
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
    assetMeta,
    toggleStage,
  });
}
