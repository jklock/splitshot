export function createMergePane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  getMergeSourceExpansion = () => new Map(),
  getMergeDraft = () => ({}),
  getPendingMergeSourcePayloads = () => new Map(),
  getMergeSourceCommitTimers = () => new Map(),
  normalizedCoordinateValue = (value) => value,
  clampNumber = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value)),
  opacityPercentValue = (value) => Math.round(Number(value || 0) * 100),
  opacityValueFromPercent = (value) => clampNumber(Number(value || 0), 0, 100) / 100,
  syncControlValue = () => {},
  preserveElementViewportAnchor = (_locator, callback) => callback(),
  withPreservedScrollState = (_elements, callback) => callback(),
  scheduleInteractionPreviewRender = () => {},
  scheduleSecondaryPreviewSync = () => {},
  renderLiveOverlay = () => {},
  renderVideo = () => {},
  callApi = async () => null,
  activity = () => {},
  autoApplyMerge = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  fileName = (value) => String(value || ""),
  buildMediaUrl = (value) => value,
  previewFrameGeometry = () => null,
  pipDefaultsSectionId = "pip-defaults",
  sendKeepaliveJson = () => false,
  setStatus = () => {},
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function currentMergeSourceExpansion() {
    return getMergeSourceExpansion() || new Map();
  }

  function currentMergeDraft() {
    const draft = getMergeDraft();
    return draft && typeof draft === "object" ? draft : {};
  }

  function currentPendingMergeSourcePayloads() {
    return getPendingMergeSourcePayloads() || new Map();
  }

  function currentMergeSourceCommitTimers() {
    return getMergeSourceCommitTimers() || new Map();
  }

    function normalizeMergeDraftValue(key, value) {
      if (!["enabled", "layout", "pip_size_percent", "pip_x", "pip_y", "placement_mode"].includes(key)) {
        return undefined;
      }
      if (key === "enabled") return Boolean(value);
      if (key === "layout" || key === "placement_mode") return String(value || "side_by_side");
      if (key === "pip_size_percent") {
        return clampNumber(Number(value) || 35, 1, 95);
      }
      return normalizedCoordinateValue(value) ?? 1;
    }

    function applyMergeDraft(payload = {}) {
      const mergeState = currentState()?.project?.merge;
      Object.entries(payload).forEach(([key, value]) => {
        const normalized = normalizeMergeDraftValue(key, value);
        if (normalized === undefined) return;
        currentMergeDraft()[key] = normalized;
        if (mergeState) mergeState[key] = normalized;
      });
    }

    function mergeMergeDraft(project) {
      const mergeState = project?.merge;
      if (!mergeState) return;
      Object.entries(currentMergeDraft()).forEach(([key, value]) => {
        const savedValue = normalizeMergeDraftValue(key, mergeState[key]);
        if (Object.is(value, savedValue)) {
          delete currentMergeDraft()[key];
        } else {
          mergeState[key] = value;
        }
      });
    }

    function currentPipSizePercent(source = null, fallback = 35) {
      const sourceSize = Number(source?.pip_size_percent);
      if (Number.isFinite(sourceSize) && sourceSize > 0) return sourceSize;
      return Number(
        currentState()?.project?.merge?.pip_size_percent
          ?? Number(String(currentState()?.project?.merge?.pip_size || "35%").replace(/%$/, ""))
          ?? fallback,
      );
    }

    function sourceIdentifier(source, fallback = "") {
      const asset = source?.asset || source || {};
      return source?.id || asset.id || fallback || fileName(asset.path || "");
    }

    function currentSourceSyncOffsetMs(source = null) {
      return Math.round(Number(source?.sync_offset_ms) || 0);
    }

    function currentSourceOpacity(source = null) {
      return clampNumber(Number(source?.opacity ?? 1) || 0, 0, 1);
    }

    function currentSourceAngleRole(source = null) {
      return String(source?.camera_role || source?.angle_role || "follow");
    }

    function normalizedAngleRoleValue(value) {
      const roles = ["primary", "follow", "static", "detail"];
      const normalized = String(value || "").trim().toLowerCase();
      return roles.includes(normalized) ? normalized : "follow";
    }

    function currentSourcePlacementMode(source = null) {
      return String(source?.placement?.mode || "auto");
    }

    function resolvedSourcePlacementMode(source = null) {
      const explicitMode = currentSourcePlacementMode(source);
      if (explicitMode && explicitMode !== "auto") return explicitMode;
      return String(currentState()?.project?.merge?.layout || "side_by_side");
    }

    function normalizedPlacementModeValue(value) {
      const modes = ["auto", "base", "side_by_side", "above_below", "pip", "full_screen_portrait", "dual_center_hud", "dual_top_hud"];
      const normalized = String(value || "").trim().toLowerCase();
      return modes.includes(normalized) ? normalized : currentState()?.project?.merge?.layout || "side_by_side";
    }

    function placementModeLabel(mode) {
      return {
        auto: "Project default",
        base: "Base (video stage)",
        side_by_side: "Side by side",
        above_below: "Above / below",
        pip: "Picture in picture",
        full_screen_portrait: "Full-screen portrait",
        dual_center_hud: "Dual center HUD",
        dual_top_hud: "Dual top HUD",
      }[mode] || mode;
    }

    function formatSyncOffsetLabel(offsetMs) {
      const numeric = Math.round(Number(offsetMs) || 0);
      return `${numeric > 0 ? "+" : ""}${numeric} ms`;
    }

    function mergePreviewTargetTime(primaryTime, source = null) {
      return Math.max(0, primaryTime + (currentSourceSyncOffsetMs(source) / 1000));
    }

    function mergeSourceById(sourceId) {
      return (currentState()?.project?.merge_sources || []).find((source, index) => sourceIdentifier(source, String(index)) === sourceId) || null;
    }

    function isMergeSourceExpanded(sourceId) {
      if (!sourceId) return false;
      if (currentMergeSourceExpansion().has(sourceId)) return Boolean(currentMergeSourceExpansion().get(sourceId));
      if (sourceId === pipDefaultsSectionId) return true;
      const firstSource = currentState()?.project?.merge_sources?.[0] || null;
      if (firstSource && sourceId === sourceIdentifier(firstSource, "0")) return true;
      return false;
    }

    function setMergeSourceExpanded(sourceId, expanded) {
      if (!sourceId) return;
      currentMergeSourceExpansion().set(sourceId, Boolean(expanded));
      syncLocalProjectUiState();
      scheduleProjectUiStateApply();
    }

    function syncMergeSourceControls(sourceId, pipX, pipY, pipSizePercent = null, syncOffsetMs = null, opacity = null) {
      const xValue = Number.isFinite(pipX) ? pipX.toFixed(3) : "";
      const yValue = Number.isFinite(pipY) ? pipY.toFixed(3) : "";
      const sizeValue = Number.isFinite(pipSizePercent) ? Math.round(pipSizePercent) : "";
      const offsetValue = Math.round(Number(syncOffsetMs) || 0);
      const opacityValue = String(opacityPercentValue(opacity ?? 1));
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="x"]`).forEach((input) => {
        syncControlValue(input, xValue);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="y"]`).forEach((input) => {
        syncControlValue(input, yValue);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="size"]`).forEach((input) => {
        syncControlValue(input, sizeValue);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-output="size"]`).forEach((output) => {
        output.textContent = sizeValue === "" ? "" : `${sizeValue}%`;
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="opacity"]`).forEach((input) => {
        syncControlValue(input, opacityValue);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="placement_mode"]`).forEach((input) => {
        const source = mergeSourceById(sourceId);
        syncControlValue(input, currentSourcePlacementMode(source));
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-sync-label]`).forEach((label) => {
        label.textContent = formatSyncOffsetLabel(offsetValue);
      });
    }

    function updateLocalMergeSourcePosition(sourceId, pipX, pipY, pipSizePercent = null, opacity = null) {
      const source = mergeSourceById(sourceId);
      if (!source || !currentState()?.project) return;
      const nextSize = clampNumber(
        Number(
          pipSizePercent
            ?? source.pip_size_percent
            ?? currentState().project.merge.pip_size_percent
            ?? 35,
        ) || 35,
        1,
        95,
      );
      const nextX = normalizedCoordinateValue(pipX) ?? 1;
      const nextY = normalizedCoordinateValue(pipY) ?? 1;
      const nextOpacity = currentSourceOpacity({ opacity: opacity ?? source.opacity ?? 1 });
      source.pip_size_percent = nextSize;
      source.pip_x = nextX;
      source.pip_y = nextY;
      source.opacity = nextOpacity;
      syncMergeSourceControls(sourceId, nextX, nextY, nextSize, source.sync_offset_ms, nextOpacity);
    }

    function updateLocalMergeSourceSyncOffset(sourceId, syncOffsetMs) {
      const source = mergeSourceById(sourceId);
      if (!source || !currentState()?.project) return;
      source.sync_offset_ms = Math.round(Number(syncOffsetMs) || 0);
      if (currentState().project.merge_sources?.[0]?.id === sourceId) {
        currentState().project.analysis.sync_offset_ms = source.sync_offset_ms;
      }
      syncMergeSourceControls(
        sourceId,
        normalizedCoordinateValue(source.pip_x),
        normalizedCoordinateValue(source.pip_y),
        currentPipSizePercent(source),
        source.sync_offset_ms,
        currentSourceOpacity(source),
      );
    }

    function mergeSourcePositionPayload(sourceId, source) {
      return {
        source_id: sourceId,
        pip_size_percent: currentPipSizePercent(source, currentPipSizePercent()),
        pip_x: normalizedCoordinateValue(source?.pip_x) ?? 1,
        pip_y: normalizedCoordinateValue(source?.pip_y) ?? 1,
        opacity: currentSourceOpacity(source),
      };
    }

    function syncMergePreviewStateFromControls() {
      if (!currentState()?.project) return;
      const merge = currentState().project.merge;
      merge.enabled = $("merge-enabled").checked;
      merge.layout = $("merge-layout").value;
      merge.pip_size_percent = clampNumber(Number($("pip-size").value) || 35, 1, 95);
      merge.pip_x = normalizedCoordinateValue($("pip-x").value) ?? 1;
      merge.pip_y = normalizedCoordinateValue($("pip-y").value) ?? 1;
    }

  function mergePreviewSafeRect(frameRect) {
    const video = $("primary-video");
    if (!(video instanceof HTMLVideoElement) || !video.controls) return frameRect;
    const controlReserve = Math.min(64, Math.max(42, frameRect.height * 0.1));
    return {
      ...frameRect,
      height: Math.max(1, frameRect.height - controlReserve),
      controlReserve,
    };
  }

  function mergeSourcePipRect(source, frameRect, pipSizeValue = null) {
    const safeRect = mergePreviewSafeRect(frameRect);
    const asset = source.asset || source;
    const sourceWidth = Math.max(1, asset.width || 1);
    const sourceHeight = Math.max(1, asset.height || 1);
    const effectivePipSize = currentPipSizePercent(source, pipSizeValue ?? 35);
    let insetWidth = Math.max(1, Math.round(frameRect.width * (effectivePipSize / 100)));
    let insetHeight = Math.max(1, Math.round((sourceHeight / sourceWidth) * insetWidth));
    if (insetHeight > safeRect.height) {
      const fitScale = safeRect.height / insetHeight;
      insetWidth = Math.max(1, Math.round(insetWidth * fitScale));
      insetHeight = Math.max(1, Math.round(insetHeight * fitScale));
    }
    const travelX = Math.max(0, safeRect.width - insetWidth);
    const travelY = Math.max(0, safeRect.height - insetHeight);
    const pipX = normalizedCoordinateValue(source.pip_x) ?? normalizedCoordinateValue(currentState().project.merge.pip_x) ?? 1;
    const pipY = normalizedCoordinateValue(source.pip_y) ?? normalizedCoordinateValue(currentState().project.merge.pip_y) ?? 1;
    return {
      left: safeRect.left + (travelX * pipX),
      top: safeRect.top + (travelY * pipY),
      width: insetWidth,
      height: insetHeight,
    };
  }

  function mergeSourcePreviewRect(source, frameRect, pipSizeValue = null, sourceIndex = 0, totalSources = 1) {
    const mode = resolvedSourcePlacementMode(source);
    const role = currentSourceAngleRole(source);
    if (mode === "pip") {
      return mergeSourcePipRect(source, frameRect, pipSizeValue);
    }
    if (mode === "side_by_side") {
      const width = Math.max(1, Math.round(frameRect.width / 2));
      const prefersLeadingSlot = role === "primary";
      const isLeadingSlot = totalSources <= 1 ? false : (sourceIndex % 2 === 0 ? prefersLeadingSlot : !prefersLeadingSlot);
      return {
        left: frameRect.left + (isLeadingSlot ? 0 : frameRect.width - width),
        top: frameRect.top,
        width,
        height: frameRect.height,
      };
    }
    if (mode === "above_below") {
      const height = Math.max(1, Math.round(frameRect.height / 2));
      const prefersTopSlot = role === "primary";
      const isTopSlot = totalSources <= 1 ? false : (sourceIndex % 2 === 0 ? prefersTopSlot : !prefersTopSlot);
      return {
        left: frameRect.left,
        top: frameRect.top + (isTopSlot ? 0 : frameRect.height - height),
        width: frameRect.width,
        height,
      };
    }
    if (mode === "base" || mode === "full_screen_portrait") {
      return {
        left: frameRect.left,
        top: frameRect.top,
        width: frameRect.width,
        height: frameRect.height,
      };
    }
    const centeredPipX = 0.5;
    const centeredPipY = mode === "dual_top_hud" ? 0.04 : 0.5;
    return mergeSourcePipRect(
      {
        ...source,
        pip_x: centeredPipX,
        pip_y: centeredPipY,
      },
      frameRect,
      pipSizeValue ?? Math.max(35, currentPipSizePercent(source, 35)),
    );
  }

  function ensureMergePreviewItem(layer, source) {
    const asset = source.asset || source;
    const sourceId = sourceIdentifier(source, fileName(asset.path || ""));
    const activePath = source?.effective_media_path || asset.path || "";
    const activeDisplayName = source?.active_display_name || fileName(activePath || asset.path || "");
    let item = layer.querySelector(`.merge-preview-item[data-source-id="${sourceId}"]`);
    if (!item) {
      item = documentObject.createElement("div");
      item.className = "merge-preview-item";
      item.dataset.sourceId = sourceId;
      layer.appendChild(item);
    }
    item.dataset.sourceId = sourceId;
    item.dataset.mediaType = asset.is_still_image ? "image" : "video";
    let media = item.firstElementChild;
    const desiredTag = asset.is_still_image ? "IMG" : "VIDEO";
    if (!(media instanceof HTMLElement) || media.tagName !== desiredTag) {
      item.innerHTML = "";
      media = documentObject.createElement(asset.is_still_image ? "img" : "video");
      if (media instanceof HTMLVideoElement) {
        media.defaultMuted = false;
        media.muted = false;
        media.volume = 1;
        media.playsInline = true;
        media.disablePictureInPicture = true;
        media.preload = "metadata";
        ["loadedmetadata", "loadeddata"].forEach((eventName) => {
          media.addEventListener(eventName, () => {
            scheduleSecondaryPreviewSync();
            renderLiveOverlay();
          });
        });
      }
      item.appendChild(media);
    }
    const mediaPath = buildMediaUrl(`/media/merge/${sourceId}`, activePath);
    if (media instanceof HTMLImageElement) {
      if (media.dataset.sourcePath !== activePath || media.dataset.mediaUrl !== mediaPath) {
        media.dataset.sourcePath = activePath;
        media.dataset.mediaUrl = mediaPath;
        media.src = mediaPath;
      }
    } else if (media instanceof HTMLVideoElement && (media.dataset.sourcePath !== activePath || media.dataset.mediaUrl !== mediaPath)) {
      media.dataset.sourcePath = activePath;
      media.dataset.mediaUrl = mediaPath;
      media.src = mediaPath;
      media.load();
    }
    if (media instanceof HTMLImageElement) {
      media.style.opacity = String(currentSourceOpacity(source));
    } else if (media instanceof HTMLVideoElement) {
      media.style.opacity = String(currentSourceOpacity(source));
    }
    return item;
  }

  function renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue) {
    const layer = $("merge-preview-layer");
    if (!layer) return;
    if (!($("show-pip")?.checked ?? true)) {
      layer.hidden = true;
      layer.innerHTML = "";
      return;
    }
    const frameRect = previewFrameGeometry(video, stage)?.frameRect;
    if (!frameRect || mergeSources.length === 0) {
      layer.hidden = true;
      layer.innerHTML = "";
      return;
    }
    layer.hidden = false;
    const expectedIds = new Set(mergeSources.map((source, index) => sourceIdentifier(source, String(index))));
    layer.querySelectorAll(".merge-preview-item[data-source-id]").forEach((item) => {
      if (!expectedIds.has(item.dataset.sourceId)) item.remove();
    });
    mergeSources.forEach((source, index) => {
      const item = ensureMergePreviewItem(layer, source);
      const activeDisplayName = source?.active_display_name || fileName(source?.effective_media_path || source?.asset?.path || "");
      const rect = mergeSourcePreviewRect(source, frameRect, pipSizeValue, index, mergeSources.length);
      item.style.left = `${rect.left}px`;
      item.style.top = `${rect.top}px`;
      item.style.width = `${rect.width}px`;
      item.style.height = `${rect.height}px`;
      item.style.maxWidth = `${rect.width}px`;
      item.style.maxHeight = `${rect.height}px`;
      item.dataset.placementMode = resolvedSourcePlacementMode(source);
      item.title = `${index + 1}. ${activeDisplayName}`;
    });
  }

  function clearMergeSourceCommitTimers({ clearPayloads = false } = {}) {
    currentMergeSourceCommitTimers().forEach((timerId) => windowObject.clearTimeout(timerId));
    currentMergeSourceCommitTimers().clear();
    if (clearPayloads) currentPendingMergeSourcePayloads().clear();
  }

  function scheduleMergeSourceCommit(payload, { immediate = false } = {}) {
    const sourceId = payload?.source_id;
    if (!sourceId) return;
    currentPendingMergeSourcePayloads().set(sourceId, payload);
    const existingTimer = currentMergeSourceCommitTimers().get(sourceId);
    if (existingTimer !== undefined) windowObject.clearTimeout(existingTimer);
    if (immediate) {
      currentMergeSourceCommitTimers().delete(sourceId);
      void flushPendingMergeSourceCommits();
      return;
    }
    const timerId = windowObject.setTimeout(() => {
      currentMergeSourceCommitTimers().delete(sourceId);
      const nextPayload = currentPendingMergeSourcePayloads().get(sourceId);
      currentPendingMergeSourcePayloads().delete(sourceId);
      if (nextPayload) {
        autoApplyMerge.flush?.();
        callApi("/api/merge/source", nextPayload);
        setStatus("Applied source layout.");
      }
    }, 120);
    currentMergeSourceCommitTimers().set(sourceId, timerId);
  }

  async function flushPendingMergeSourceCommits({ keepalive = false } = {}) {
    if (currentPendingMergeSourcePayloads().size === 0) return;
    clearMergeSourceCommitTimers();
    const pendingPayloads = [...currentPendingMergeSourcePayloads().values()];
    currentPendingMergeSourcePayloads().clear();
    if (keepalive) {
      pendingPayloads.forEach((payload) => sendKeepaliveJson("/api/merge/source", payload));
      return;
    }
    autoApplyMerge.flush?.();
    for (const payload of pendingPayloads) {
      await callApi("/api/merge/source", payload);
    }
  }

  function renderMergeMediaList() {
    const list = $("merge-media-list");
    if (!list) return;
    const syncLabel = $("sync-offset");
    const mergeSources = currentState()?.project?.merge_sources || [];
    if (syncLabel) syncLabel.textContent = `${mergeSources.length} source${mergeSources.length === 1 ? "" : "s"}`;
    const validSourceIds = new Set(mergeSources.map((source, index) => sourceIdentifier(source, String(index))));
    [...currentMergeSourceExpansion().keys()].forEach((sourceId) => {
      if (sourceId !== pipDefaultsSectionId && !validSourceIds.has(sourceId)) currentMergeSourceExpansion().delete(sourceId);
    });
    withPreservedScrollState([list], () => {
      list.innerHTML = "";
      if (mergeSources.length === 0) {
        return;
      }

      mergeSources.forEach((source, index) => {
        const asset = source.asset || source;
        const sourceId = sourceIdentifier(source, String(index));
        const card = documentObject.createElement("div");
        card.className = "merge-media-card";
        card.dataset.sourceId = sourceId;
        const expanded = isMergeSourceExpanded(sourceId);
        card.classList.toggle("collapsed", !expanded);

        const header = documentObject.createElement("div");
        header.className = "merge-media-card-header";
        header.classList.add("section-header-with-toggle");
        const copy = documentObject.createElement("div");
        copy.className = "merge-media-card-copy";
        const title = documentObject.createElement("strong");
        title.textContent = source?.active_display_name || fileName(source?.effective_media_path || asset.path || "");

        const toggle = documentObject.createElement("button");
        toggle.type = "button";
        toggle.className = "pane-toggle";
        toggle.textContent = expanded ? "v" : ">";
        toggle.title = expanded ? "Hide stage media controls" : "Show stage media controls";
        toggle.setAttribute("aria-label", `${expanded ? "Hide" : "Show"} stage media controls`);
        toggle.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          preserveElementViewportAnchor(
            () => documentObject.querySelector(`.merge-media-card[data-source-id="${sourceId}"]`),
            () => {
              setMergeSourceExpanded(sourceId, !expanded);
              renderMergeMediaList();
            },
          );
        });

        const headerActions = documentObject.createElement("div");
        headerActions.className = "merge-media-card-actions";
        headerActions.append(toggle);
        const meta = documentObject.createElement("small");
        meta.className = "merge-media-card-meta";
        const mediaType = asset.is_still_image ? "Image" : "Video";
        const dimensions = asset.width && asset.height ? ` · ${asset.width}×${asset.height}` : "";
        meta.textContent = `${mediaType}${dimensions}`;
        copy.append(title, meta);
        header.append(copy, headerActions);

        const controls = documentObject.createElement("div");
        controls.className = "merge-source-controls";

        const readSourcePayload = () => {
          const nextSize = clampNumber(Number(controls.querySelector('[data-merge-source-field="size"]')?.value) || 35, 1, 95);
          const nextX = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="x"]')?.value) ?? 1;
          const nextY = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="y"]')?.value) ?? 1;
          const opacityControl = controls.querySelector('[data-merge-source-field="opacity"]');
          const nextOpacity = opacityControl ? opacityValueFromPercent(opacityControl.value) : currentSourceOpacity(source);
          const placementModeControl = controls.querySelector('[data-merge-source-field="placement_mode"]');
          const nextPlacementMode = placementModeControl ? normalizedPlacementModeValue(placementModeControl.value) : currentSourcePlacementMode(source);
          const payload = {
            source_id: sourceId,
            pip_size_percent: nextSize,
            pip_x: nextX,
            pip_y: nextY,
            opacity: nextOpacity,
            placement: { mode: nextPlacementMode },
          };
          return payload;
        };

        const previewSourceUpdate = () => {
          const payload = readSourcePayload();
          const src = mergeSourceById(sourceId);
          if (payload.placement && payload.placement.mode) {
            if (src) {
              if (!src.placement) src.placement = {};
              src.placement.mode = payload.placement.mode;
            }
          }
          updateLocalMergeSourcePosition(sourceId, payload.pip_x, payload.pip_y, payload.pip_size_percent, payload.opacity);
          scheduleInteractionPreviewRender({ video: true });
          return payload;
        };

        const buildSourceNumberInput = (labelText, field, value, min, max, step, titleText) => {
          const label = documentObject.createElement("label");
          label.className = "merge-source-field";
          const text = documentObject.createElement("span");
          text.textContent = labelText;
          const input = documentObject.createElement("input");
          input.type = "number";
          input.min = String(min);
          input.max = String(max);
          input.step = String(step);
          input.value = value;
          input.dataset.mergeSourceField = field;
          input.dataset.sourceId = sourceId;
          input.title = titleText;
          input.addEventListener("input", previewSourceUpdate);
          input.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
          input.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
          label.append(text, input);
          return label;
        };

        const sizeField = documentObject.createElement("label");
        sizeField.className = "merge-source-field merge-source-size-field";
        const sizeText = documentObject.createElement("span");
        sizeText.textContent = "Size";
        const sizeControl = documentObject.createElement("span");
        sizeControl.className = "pip-size-control";
        const sizeInput = documentObject.createElement("input");
        sizeInput.type = "range";
        sizeInput.min = "1";
        sizeInput.max = "95";
        sizeInput.step = "1";
        sizeInput.value = String(currentPipSizePercent(source, currentPipSizePercent()));
        sizeInput.dataset.mergeSourceField = "size";
        sizeInput.dataset.sourceId = sourceId;
        sizeInput.title = "1 is smallest, 95 is largest.";
        sizeInput.addEventListener("input", () => {
          const output = sizeField.querySelector('[data-merge-source-output="size"]');
          if (output) output.textContent = `${sizeInput.value}%`;
          previewSourceUpdate();
        });
        sizeInput.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
        sizeInput.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
        const sizeOutput = documentObject.createElement("output");
        sizeOutput.dataset.mergeSourceOutput = "size";
        sizeOutput.dataset.sourceId = sourceId;
        sizeOutput.textContent = `${sizeInput.value}%`;
        sizeControl.append(sizeInput, sizeOutput);
        sizeField.append(sizeText, sizeControl);

        const buildSourceOpacityInput = () => {
          const label = documentObject.createElement("label");
          label.className = "merge-source-field merge-source-opacity-field";
          const text = documentObject.createElement("span");
          text.textContent = "Opacity";
          const percentField = documentObject.createElement("span");
          percentField.className = "opacity-percent-field";
          const input = documentObject.createElement("input");
          input.type = "number";
          input.className = "opacity-percent-input";
          input.min = "0";
          input.max = "100";
          input.step = "1";
          input.value = String(opacityPercentValue(currentSourceOpacity(source)));
          input.dataset.mergeSourceField = "opacity";
          input.dataset.sourceId = sourceId;
          input.title = "0 is transparent, 100 is opaque.";
          input.addEventListener("input", previewSourceUpdate);
          input.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
          input.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
          const suffix = documentObject.createElement("span");
          suffix.className = "opacity-percent-suffix";
          suffix.textContent = "%";
          percentField.append(input, suffix);
          label.append(text, percentField);
          return label;
        };

        const syncField = documentObject.createElement("div");
        syncField.className = "merge-source-field merge-source-sync-field";
        const syncFieldLabel = documentObject.createElement("span");
        syncFieldLabel.textContent = "Sync";
        const syncFieldValue = documentObject.createElement("strong");
        syncFieldValue.className = "merge-source-sync-inline";
        syncFieldValue.dataset.mergeSourceSyncLabel = "true";
        syncFieldValue.dataset.sourceId = sourceId;
        syncFieldValue.textContent = formatSyncOffsetLabel(currentSourceSyncOffsetMs(source));
        syncField.append(syncFieldLabel, syncFieldValue);

        const placementModeSelect = documentObject.createElement("select");
        placementModeSelect.dataset.mergeSourceField = "placement_mode";
        placementModeSelect.dataset.sourceId = sourceId;
        placementModeSelect.title = "Control how this item is placed in the output.";
        ["auto", "side_by_side", "above_below", "pip", "full_screen_portrait", "dual_center_hud", "dual_top_hud"].forEach((mode) => {
          const option = documentObject.createElement("option");
          option.value = mode;
          option.textContent = placementModeLabel(mode);
          if (mode === currentSourcePlacementMode(source)) option.selected = true;
          placementModeSelect.appendChild(option);
        });
        placementModeSelect.addEventListener("change", () => {
          previewSourceUpdate();
          scheduleMergeSourceCommit(readSourcePayload(), { immediate: true });
        });
        const placementModeLabelEl = documentObject.createElement("label");
        placementModeLabelEl.className = "merge-source-field merge-source-layout-field";
        placementModeLabelEl.append(documentObject.createElement("span"));
        placementModeLabelEl.querySelector("span").textContent = "Layout";
        placementModeLabelEl.append(placementModeSelect);
        const opacityField = buildSourceOpacityInput();

        const positionXField = buildSourceNumberInput("Position X", "x", normalizedCoordinateValue(source.pip_x) ?? 1, 0, 1, 0.01, "0 is left, 1 is right.");
        positionXField.classList.add("merge-source-position-field");
        const positionYField = buildSourceNumberInput("Position Y", "y", normalizedCoordinateValue(source.pip_y) ?? 1, 0, 1, 0.01, "0 is top, 1 is bottom.");
        positionYField.classList.add("merge-source-position-field");

        controls.append(
          sizeField,
          opacityField,
          placementModeLabelEl,
          positionXField,
          positionYField,
          syncField,
        );

        const body = documentObject.createElement("div");
        body.className = "merge-media-card-body";
        body.hidden = !expanded;
        body.append(controls);
        card.append(header, body);
        syncMergeSourceControls(
          sourceId,
          normalizedCoordinateValue(source.pip_x),
          normalizedCoordinateValue(source.pip_y),
          currentPipSizePercent(source),
          currentSourceSyncOffsetMs(source),
          currentSourceOpacity(source),
        );
        list.appendChild(card);
      });
    });
  }

  function readMergePayload() {
    const pipValue = Number($("pip-size").value);
    return {
      enabled: $("merge-enabled").checked,
      layout: $("merge-layout").value,
      pip_size_percent: Number.isFinite(pipValue) ? clampNumber(pipValue, 1, 95) : 35,
      pip_x: normalizedCoordinateValue($("pip-x").value) ?? 1,
      pip_y: normalizedCoordinateValue($("pip-y").value) ?? 1,
    };
  }

  function scheduleMergeApply() {
    const payload = readMergePayload();
    applyMergeDraft(payload);
    autoApplyMerge(payload);
    setStatus("Applied stage compose defaults.");
  }

  return Object.freeze({
    normalizeMergeDraftValue,
    applyMergeDraft,
    mergeMergeDraft,
    currentPipSizePercent,
    sourceIdentifier,
    currentSourceSyncOffsetMs,
    currentSourceOpacity,
    currentSourceAngleRole,
    normalizedAngleRoleValue,
    currentSourcePlacementMode,
    resolvedSourcePlacementMode,
    normalizedPlacementModeValue,
    placementModeLabel,
    formatSyncOffsetLabel,
    mergePreviewTargetTime,
    mergeSourceById,
    isMergeSourceExpanded,
    setMergeSourceExpanded,
    syncMergeSourceControls,
    updateLocalMergeSourcePosition,
    updateLocalMergeSourceSyncOffset,
    mergeSourcePositionPayload,
    syncMergePreviewStateFromControls,
    mergeSourcePipRect,
    mergeSourcePreviewRect,
    ensureMergePreviewItem,
    renderMergePreviewLayer,
    clearMergeSourceCommitTimers,
    scheduleMergeSourceCommit,
    flushPendingMergeSourceCommits,
    renderMergeMediaList,
    readMergePayload,
    scheduleMergeApply,
  });
}
