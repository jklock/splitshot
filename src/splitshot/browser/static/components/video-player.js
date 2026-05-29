export function createVideoPlayerComponent({
  $ = (id) => document.getElementById(id),
  getState = () => null,
  getSelectedShotId = () => null,
  maybeApplyRecommendedLayout = () => {},
  buildMediaUrl = (url) => url,
  resetMediaElement = () => {},
  isImagePath = () => false,
  ensurePrimaryVideoAudio = () => {},
  logPrimaryVideoState = () => {},
  currentPipSizePercent = () => 35,
  previewFrameGeometry = () => null,
  normalizedCoordinateValue = (value) => value,
  sourceIdentifier = (source, fallback = "") => source?.id || source?.asset?.id || fallback,
  resolvedMergeSourcePreviewPlacement = () => ({
    mode: "side_by_side",
    slot: "right",
    target_kind: "primary_video",
    target_source_id: null,
  }),
  mergeSourceUsesFreeformPreviewDrag = () => false,
  currentSourceOpacity = () => 1,
  mergeSourcePipRect = () => ({ left: 0, top: 0, width: 1, height: 1 }),
  renderMergePreviewLayer = () => {},
  scheduleSecondaryPreviewSync = () => {},
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function renderVideo() {
    const state = currentState();
    maybeApplyRecommendedLayout();
    const video = $("primary-video");
    const secondary = $("secondary-video");
    const secondaryImage = $("secondary-image");
    const mergePreviewLayer = $("merge-preview-layer");
    const stage = $("video-stage");
    const merge = state.project.merge;
    const mergeSources = state?.project?.merge_sources || [];
    const path = state.project.primary_video.path || "";
    const primaryMediaPath = buildMediaUrl(state.media.primary_url || "/media/primary", path);
    if (state.media.primary_available && (video.dataset.sourcePath !== path || video.dataset.mediaUrl !== primaryMediaPath)) {
      video.dataset.sourcePath = path;
      video.dataset.mediaUrl = primaryMediaPath;
      video.src = primaryMediaPath;
      video.load();
      logPrimaryVideoState("source.attach");
    }
    if (!state.media.primary_available) {
      resetMediaElement(video);
    }

    const secondaryPath = state.project.secondary_video?.path || "";
    const imageSecondary = isImagePath(secondaryPath);
    const secondaryMediaPath = buildMediaUrl(state.media.secondary_url || "/media/secondary", secondaryPath);
    if (state.media.secondary_available && imageSecondary) {
      if (secondaryImage.dataset.sourcePath !== secondaryPath || secondaryImage.dataset.mediaUrl !== secondaryMediaPath) {
        secondaryImage.dataset.sourcePath = secondaryPath;
        secondaryImage.dataset.mediaUrl = secondaryMediaPath;
        secondaryImage.src = secondaryMediaPath;
      }
      resetMediaElement(secondary);
    } else if (state.media.secondary_available && !imageSecondary) {
      if (secondary.dataset.sourcePath !== secondaryPath || secondary.dataset.mediaUrl !== secondaryMediaPath) {
        secondary.dataset.sourcePath = secondaryPath;
        secondary.dataset.mediaUrl = secondaryMediaPath;
        secondary.src = secondaryMediaPath;
        ensurePrimaryVideoAudio(secondary);
        secondary.load();
      }
      secondaryImage.removeAttribute("src");
    } else {
      resetMediaElement(secondary);
      secondaryImage.removeAttribute("src");
      secondaryImage.hidden = true;
    }

    const mergePreview = Boolean(merge.enabled && mergeSources.length > 0);
    const mergeSourceMap = new Map(
      mergeSources.map((source, index) => [sourceIdentifier(source, String(index)), source]),
    );
    if (mergePreviewLayer) {
      mergePreviewLayer.hidden = true;
      if (!mergePreview) mergePreviewLayer.innerHTML = "";
    }
    stage.classList.toggle("merge-preview", mergePreview);
    stage.classList.toggle("merge-side-by-side", false);
    stage.classList.toggle("merge-above-below", false);
    stage.classList.toggle("merge-pip", false);
    stage.classList.toggle("merge-full-screen-portrait", false);
    stage.classList.toggle("merge-dual-center-hud", false);
    stage.classList.toggle("merge-dual-top-hud", false);

    const frameGeometry = mergePreview ? null : previewFrameGeometry(video, stage);
    const pipSizeValue = currentPipSizePercent();
    stage.style.setProperty("--pip-size", `${pipSizeValue}%`);
    if (frameGeometry) {
      const cropCenterX = normalizedCoordinateValue(state.project.export.crop_center_x) ?? 0.5;
      const cropCenterY = normalizedCoordinateValue(state.project.export.crop_center_y) ?? 0.5;
      video.hidden = false;
      video.style.position = "absolute";
      video.style.left = `${frameGeometry.frameRect.left}px`;
      video.style.top = `${frameGeometry.frameRect.top}px`;
      video.style.width = `${frameGeometry.frameRect.width}px`;
      video.style.height = `${frameGeometry.frameRect.height}px`;
      video.style.maxWidth = "none";
      video.style.maxHeight = "none";
      video.style.right = "";
      video.style.bottom = "";
      video.style.objectFit = "cover";
      video.style.objectPosition = `${cropCenterX * 100}% ${cropCenterY * 100}%`;
      video.style.zIndex = "0";
    } else {
      video.style.position = "";
      video.style.left = "";
      video.style.top = "";
      video.style.width = "";
      video.style.height = "";
      video.style.maxWidth = "";
      video.style.maxHeight = "";
      video.style.right = "";
      video.style.bottom = "";
      video.style.objectFit = "";
      video.style.objectPosition = "";
      video.style.zIndex = "";
    }
    [secondary, secondaryImage].forEach((element) => {
      element.style.position = "";
      element.style.left = "";
      element.style.top = "";
      element.style.right = "";
      element.style.bottom = "";
      element.style.width = "";
      element.style.height = "";
      element.style.maxWidth = "";
      element.style.maxHeight = "";
      element.style.opacity = "";
      element.style.zIndex = "";
    });

    if (mergePreview && mergeSources.length > 0) {
      renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue);
      mergePreviewLayer?.querySelectorAll(".merge-preview-item[data-source-id]").forEach((item) => {
        const source = mergeSourceMap.get(item.dataset.sourceId || "") || null;
        const dragEnabled = Boolean(source && mergeSourceUsesFreeformPreviewDrag(source));
        item.dataset.dragEnabled = dragEnabled ? "true" : "false";
        item.style.cursor = dragEnabled ? "" : "default";
        item.style.touchAction = dragEnabled ? "none" : "auto";
        item.dataset.placementMode = source ? resolvedMergeSourcePreviewPlacement(source).mode : "";
      });
      secondary.hidden = true;
      secondary.style.display = "none";
      secondaryImage.hidden = true;
      secondaryImage.style.display = "none";
    } else {
      const showSecondaryVideo = false;
      const showSecondaryImage = false;
      secondary.hidden = !showSecondaryVideo;
      secondary.style.display = showSecondaryVideo ? "" : "none";
      secondaryImage.hidden = !showSecondaryImage;
      secondaryImage.style.display = showSecondaryImage ? "block" : "none";
    }

    const waveformEnabled = Boolean(state.project.analysis?.shots?.length);
    document.querySelectorAll(".waveform-actions button").forEach((button) => {
      if (button.id === "amp-waveform-out" || button.id === "amp-waveform-in") {
        button.disabled = !waveformEnabled || !getSelectedShotId();
      } else {
        button.disabled = !waveformEnabled;
      }
    });
    scheduleSecondaryPreviewSync();
  }

  return Object.freeze({ renderVideo });
}
