function emitBackbone(backbone, eventName, detail = undefined) {
  backbone?.bus?.emit?.(eventName, detail);
  return detail;
}

function patchBackboneStore(backbone, patch = {}) {
  if (!backbone?.storePatch || !patch || typeof patch !== "object") return patch;
  backbone.storePatch(patch);
  return patch;
}

export function createLayoutRuntime({
  backbone = null,
  runtime,
  $,
  clamp,
  DEFAULT_LAYOUT_SIZES,
  INSPECTOR_COMPACT_WIDTH,
  computeExportCropBox,
  exportTargetDimensions,
  markersWorkbenchShown = () => false,
  scheduleInteractionPreviewRender = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  renderWaveform = () => {},
  activity = () => {},
  setWaveformExpanded = () => {},
  scheduleReviewStageRestore = () => {},
  capturePointer = () => {},
  releasePointer = () => {},
  flushInteractionPreviewRender = () => {},
  flushQueuedProjectUiStateApply = () => {},
  flushDeferredRender = () => {},
} = {}) {
  function syncLayoutBackbone() {
    patchBackboneStore(backbone, {
      railCollapsed: Boolean(runtime?.railCollapsed),
      layoutLocked: Boolean(runtime?.layoutLocked),
      layoutSizes: { ...(runtime?.layoutSizes || {}) },
      popupWorkbenchHeight: runtime?.popupWorkbenchHeight ?? null,
      activeResizeKind: runtime?.activeResize?.kind || null,
    });
  }

  function layoutViewportHeight() {
    const cockpit = document.querySelector(".cockpit");
    const documentHeight = document.documentElement?.clientHeight || 0;
    const visualViewportHeight = window.visualViewport?.height || 0;
    const cockpitHeight = cockpit?.getBoundingClientRect().height || cockpit?.clientHeight || 0;
    return Math.max(1, Math.floor(visualViewportHeight || documentHeight || window.innerHeight || cockpitHeight));
  }

  function setCssPixels(name, value) {
    document.documentElement.style.setProperty(name, `${Math.round(value)}px`);
  }

  function currentPreviewAspectRatio(video = $("primary-video")) {
    const sourceWidth = Math.max(1, Number(video?.videoWidth || runtime.state?.project?.primary_video?.width || 0) || 1);
    const sourceHeight = Math.max(1, Number(video?.videoHeight || runtime.state?.project?.primary_video?.height || 0) || 1);
    const exportSettings = runtime.state?.project?.export;
    if (!exportSettings) return sourceWidth / sourceHeight;
    const cropBox = computeExportCropBox(
      sourceWidth,
      sourceHeight,
      exportSettings.aspect_ratio,
      exportSettings.crop_center_x,
      exportSettings.crop_center_y,
    );
    const outputDimensions = exportTargetDimensions(cropBox.width, cropBox.height);
    return Math.max(0.45, Math.min(2.4, outputDimensions.width / Math.max(1, outputDimensions.height)));
  }

  function recommendedReviewLayoutSizes(viewportWidth = window.innerWidth, viewportHeight = layoutViewportHeight()) {
    const railWidth = runtime.railCollapsed ? 48 : clamp(runtime.layoutSizes.railWidth, 84, 104);
    const reviewWidth = Math.max(720, viewportWidth - railWidth - (2 * 4));
    const reviewHeight = Math.max(360, viewportHeight - 38);
    const previewAspect = currentPreviewAspectRatio();
    const inspectorMinimum = 320;
    const inspectorMaximum = Math.max(inspectorMinimum, Math.min(520, reviewWidth * 0.42));
    const targetWaveformHeight = clamp(Math.round(reviewHeight * 0.24), 144, Math.max(160, reviewHeight * 0.34));
    const preferredStageHeight = Math.max(260, reviewHeight - targetWaveformHeight - 4);
    const preferredStageWidth = preferredStageHeight * previewAspect;
    const inspectorWidth = clamp(Math.round(reviewWidth - preferredStageWidth - 4), inspectorMinimum, inspectorMaximum);
    const stageWidth = Math.max(320, reviewWidth - inspectorWidth - 4);
    const waveformHeight = clamp(
      Math.round(reviewHeight - (stageWidth / previewAspect) - 4),
      144,
      Math.max(144, reviewHeight * 0.38),
    );
    return { inspectorWidth, waveformHeight };
  }

  function maybeApplyRecommendedLayout({ force = false } = {}) {
    const shouldAdjustInspector = force || !runtime.layoutSizePinned.inspectorWidth;
    const shouldAdjustWaveform = force || !runtime.layoutSizePinned.waveformHeight;
    if (!shouldAdjustInspector && !shouldAdjustWaveform) return false;
    const recommended = recommendedReviewLayoutSizes();
    let changed = false;
    if (shouldAdjustInspector && Math.round(runtime.layoutSizes.inspectorWidth) !== Math.round(recommended.inspectorWidth)) {
      runtime.layoutSizes = {
        ...runtime.layoutSizes,
        inspectorWidth: recommended.inspectorWidth,
      };
      changed = true;
    }
    if (shouldAdjustWaveform && Math.round(runtime.layoutSizes.waveformHeight) !== Math.round(recommended.waveformHeight)) {
      runtime.layoutSizes = {
        ...runtime.layoutSizes,
        waveformHeight: recommended.waveformHeight,
      };
      changed = true;
    }
    if (changed) syncLayoutBackbone();
    return changed;
  }

  function popupWorkbenchTargetHeight(viewportHeight = layoutViewportHeight()) {
    const minimumHeight = 112;
    const maximumHeight = Math.max(minimumHeight, viewportHeight * 0.42);
    const fallbackHeight = clamp(runtime.layoutSizes.waveformHeight, minimumHeight, maximumHeight);
    return clamp(
      Math.round(Number(runtime.popupWorkbenchHeight ?? fallbackHeight) || fallbackHeight),
      minimumHeight,
      maximumHeight,
    );
  }

  function capturePopupWorkbenchRestoreState() {
    if (runtime.popupWorkbenchRestoreState) return runtime.popupWorkbenchRestoreState;
    const root = $("cockpit-root");
    runtime.popupWorkbenchRestoreState = {
      waveformExpanded: Boolean(root?.classList.contains("waveform-expanded")),
      waveformHeight: runtime.layoutSizes.waveformHeight,
      waveformHeightPinned: Boolean(runtime.layoutSizePinned.waveformHeight),
    };
    runtime.popupWorkbenchHeight = runtime.layoutSizes.waveformHeight;
    syncLayoutBackbone();
    return runtime.popupWorkbenchRestoreState;
  }

  function restorePopupWorkbenchLayout({ persistUiState = true, restoreWaveformExpanded = true } = {}) {
    const restoreState = runtime.popupWorkbenchRestoreState;
    runtime.popupWorkbenchRestoreState = null;
    runtime.popupWorkbenchHeight = null;
    if (!restoreState) {
      scheduleReviewStageRestore();
      syncLayoutBackbone();
      return;
    }
    runtime.layoutSizes = {
      ...runtime.layoutSizes,
      waveformHeight: restoreState.waveformHeight,
    };
    runtime.layoutSizePinned = {
      ...runtime.layoutSizePinned,
      waveformHeight: restoreState.waveformHeightPinned,
    };
    applyLayoutState();
    if (restoreWaveformExpanded && restoreState.waveformExpanded) {
      setWaveformExpanded(true, { persistUiState });
      syncLayoutBackbone();
      return;
    }
    syncLocalProjectUiState();
    if (persistUiState) scheduleProjectUiStateApply();
    scheduleReviewStageRestore();
    syncLayoutBackbone();
  }

  function applyLayoutState() {
    const viewportHeight = layoutViewportHeight();
    setCssPixels("--app-height", viewportHeight);
    runtime.layoutSizes = {
      railWidth: clamp(runtime.layoutSizes.railWidth, 84, 104),
      inspectorWidth: clamp(runtime.layoutSizes.inspectorWidth, 320, Math.max(320, window.innerWidth * 0.48)),
      waveformHeight: clamp(runtime.layoutSizes.waveformHeight, 112, Math.max(112, viewportHeight * 0.42)),
    };
    setCssPixels("--rail-width", runtime.railCollapsed ? 48 : runtime.layoutSizes.railWidth);
    setCssPixels("--inspector-width", runtime.layoutSizes.inspectorWidth);
    setCssPixels("--waveform-height", runtime.layoutSizes.waveformHeight);
    setCssPixels("--markers-workbench-height", popupWorkbenchTargetHeight(viewportHeight));
    const shell = document.querySelector(".cockpit-shell");
    if (shell) {
      shell.classList.toggle("layout-locked", runtime.layoutLocked);
      shell.classList.toggle("layout-unlocked", !runtime.layoutLocked);
      shell.classList.toggle("resizing-layout", runtime.activeResize !== null);
      shell.classList.toggle("inspector-compact", runtime.layoutSizes.inspectorWidth < INSPECTOR_COMPACT_WIDTH);
      shell.classList.toggle("rail-collapsed", runtime.railCollapsed);
    }
    const railToggle = $("toggle-rail");
    if (railToggle) {
      railToggle.textContent = runtime.railCollapsed ? "EXP" : railToggle.getAttribute("data-short") || "MIN";
      railToggle.title = runtime.railCollapsed ? "Expand left rail" : "Minimize left rail";
      railToggle.setAttribute("aria-label", railToggle.title);
    }
    document.querySelectorAll("[data-layout-lock-toggle]").forEach((toggle) => {
      const target = toggle.id.replace("toggle-layout-lock-", "");
      const scope = target ? `${target} layout` : "layout";
      toggle.textContent = runtime.layoutLocked ? "Lock" : "Unlock";
      toggle.setAttribute("aria-label", `${runtime.layoutLocked ? "Unlock" : "Lock"} ${scope}`);
    });
    syncLayoutBackbone();
  }

  function preserveBootstrapProjectUiState() {
    if (!runtime.initialProjectUiStateApplied) {
      runtime.pendingBootstrapProjectUiStateOverride = true;
    }
  }

  function persistLayoutSize(key, value, { renderWaveformNow = true } = {}) {
    runtime.layoutSizes = {
      ...runtime.layoutSizes,
      [key]: value,
    };
    runtime.layoutSizePinned = {
      ...runtime.layoutSizePinned,
      [key]: true,
    };
    const storageKey = {
      railWidth: "splitshot.layout.railWidth",
      inspectorWidth: "splitshot.layout.inspectorWidth",
      waveformHeight: "splitshot.layout.waveformHeight",
    }[key];
    window.localStorage.setItem(storageKey, String(Math.round(value)));
    applyLayoutState();
    preserveBootstrapProjectUiState();
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
    if (runtime.state && renderWaveformNow) renderWaveform();
    syncLayoutBackbone();
  }

  function previewLayoutSize(key, value) {
    runtime.layoutSizes = {
      ...runtime.layoutSizes,
      [key]: value,
    };
    applyLayoutState();
    scheduleInteractionPreviewRender({ video: true, waveform: true, overlay: true });
    syncLayoutBackbone();
  }

  function toggleLayoutLock() {
    runtime.layoutLocked = !runtime.layoutLocked;
    window.localStorage.setItem("splitshot.layoutLocked", String(runtime.layoutLocked));
    emitBackbone(backbone, "layout.lock.toggle", { locked: runtime.layoutLocked });
    activity("layout.lock.toggle", { locked: runtime.layoutLocked });
    applyLayoutState();
    preserveBootstrapProjectUiState();
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
    syncLayoutBackbone();
  }

  function resetLayout() {
    runtime.layoutSizes = { ...DEFAULT_LAYOUT_SIZES };
    runtime.layoutSizePinned = { railWidth: false, inspectorWidth: false, waveformHeight: false };
    ["splitshot.layout.railWidth", "splitshot.layout.inspectorWidth", "splitshot.layout.waveformHeight"].forEach((key) => {
      window.localStorage.removeItem(key);
    });
    maybeApplyRecommendedLayout({ force: true });
    emitBackbone(backbone, "layout.reset", { ...runtime.layoutSizes });
    activity("layout.reset", runtime.layoutSizes);
    applyLayoutState();
    preserveBootstrapProjectUiState();
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
    if (runtime.state) renderWaveform();
    syncLayoutBackbone();
  }

  function beginLayoutResize(kind, event) {
    if (runtime.layoutLocked) {
      emitBackbone(backbone, "layout.unlock.request", { kind });
      activity("layout.unlock.request", { kind });
      toggleLayoutLock();
      return;
    }
    runtime.activeResize = { kind, pointerId: event.pointerId, target: event.currentTarget };
    capturePointer(runtime.activeResize.target, event.pointerId);
    document.body.classList.add("resizing-layout");
    emitBackbone(backbone, "layout.resize.start", { kind });
    activity("layout.resize.start", { kind });
    applyLayoutState();
    syncLayoutBackbone();
  }

  function moveLayoutResize(event) {
    if (!runtime.activeResize) return;
    if (event.pointerId !== undefined && runtime.activeResize.pointerId !== undefined && event.pointerId !== runtime.activeResize.pointerId) return;
    const kind = runtime.activeResize.kind;
    if (kind === "railWidth") {
      previewLayoutSize("railWidth", clamp(event.clientX, 84, 104));
    } else if (kind === "inspectorWidth") {
      const grid = document.querySelector(".review-grid");
      const right = grid?.getBoundingClientRect().right || window.innerWidth;
      previewLayoutSize("inspectorWidth", clamp(right - event.clientX, 320, Math.max(320, window.innerWidth * 0.48)));
    } else if (kind === "waveformHeight") {
      const stack = document.querySelector(".review-stack");
      const rect = stack?.getBoundingClientRect();
      if (rect) {
        const nextHeight = clamp(rect.bottom - event.clientY, 112, Math.max(112, rect.height * 0.48));
        if (markersWorkbenchShown()) {
          runtime.popupWorkbenchHeight = nextHeight;
          applyLayoutState();
          scheduleInteractionPreviewRender({ video: true, waveform: true, overlay: true });
          syncLayoutBackbone();
        } else {
          previewLayoutSize("waveformHeight", nextHeight);
        }
      }
    }
  }

  function endLayoutResize(event) {
    if (!runtime.activeResize) return;
    if (event.pointerId !== undefined && runtime.activeResize.pointerId !== undefined && event.pointerId !== runtime.activeResize.pointerId) return;
    const kind = runtime.activeResize.kind;
    const sizeKey = {
      railWidth: "railWidth",
      inspectorWidth: "inspectorWidth",
      waveformHeight: "waveformHeight",
    }[kind];
    releasePointer(runtime.activeResize.target, runtime.activeResize.pointerId);
    runtime.activeResize = null;
    document.body.classList.remove("resizing-layout");
    if (sizeKey) {
      if (kind === "waveformHeight" && markersWorkbenchShown()) {
        applyLayoutState();
      } else {
        persistLayoutSize(sizeKey, runtime.layoutSizes[sizeKey], { renderWaveformNow: false });
      }
    }
    emitBackbone(backbone, "layout.resize.commit", { kind, sizes: { ...runtime.layoutSizes } });
    activity("layout.resize.commit", { kind, sizes: runtime.layoutSizes });
    flushInteractionPreviewRender();
    flushQueuedProjectUiStateApply();
    flushDeferredRender();
    syncLayoutBackbone();
  }

  syncLayoutBackbone();

  return Object.freeze({
    layoutViewportHeight,
    setCssPixels,
    currentPreviewAspectRatio,
    recommendedReviewLayoutSizes,
    maybeApplyRecommendedLayout,
    popupWorkbenchTargetHeight,
    capturePopupWorkbenchRestoreState,
    restorePopupWorkbenchLayout,
    applyLayoutState,
    persistLayoutSize,
    previewLayoutSize,
    toggleLayoutLock,
    resetLayout,
    beginLayoutResize,
    moveLayoutResize,
    endLayoutResize,
  });
}
