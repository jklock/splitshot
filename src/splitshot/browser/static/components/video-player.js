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
    if (mergePreviewLayer) {
      mergePreviewLayer.hidden = true;
      if (merge.layout !== "pip") mergePreviewLayer.innerHTML = "";
    }
    stage.classList.toggle("merge-preview", mergePreview);
    stage.classList.toggle("merge-side-by-side", mergePreview && merge.layout === "side_by_side");
    stage.classList.toggle("merge-above-below", mergePreview && merge.layout === "above_below");
    stage.classList.toggle("merge-pip", mergePreview && merge.layout === "pip");
    stage.classList.toggle(
      "merge-full-screen-portrait",
      mergePreview && merge.layout === "full_screen_portrait",
    );
    stage.classList.toggle(
      "merge-dual-center-hud",
      mergePreview && merge.layout === "dual_center_hud",
    );
    stage.classList.toggle(
      "merge-dual-top-hud",
      mergePreview && merge.layout === "dual_top_hud",
    );

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

    if (mergePreview && merge.layout === "pip" && mergeSources.length > 0) {
      renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue);
      secondary.hidden = true;
      secondary.style.display = "none";
      secondaryImage.hidden = true;
      secondaryImage.style.display = "none";
    } else {
      const showSecondaryVideo = mergePreview && !imageSecondary;
      const showSecondaryImage = mergePreview && imageSecondary;
      secondary.hidden = !showSecondaryVideo;
      secondary.style.display = showSecondaryVideo ? "" : "none";
      secondaryImage.hidden = !showSecondaryImage;
      secondaryImage.style.display = showSecondaryImage ? "block" : "none";

      if (mergePreview) {
        const activeSecondary = imageSecondary ? secondaryImage : secondary;
        activeSecondary.style.opacity = String(currentSourceOpacity(mergeSources[0] || null));
        const frameRect = previewFrameGeometry(video, stage)?.frameRect;
        const secondaryWidth = Math.max(
          1,
          imageSecondary
            ? (secondaryImage.naturalWidth || state.project.secondary_video?.width || 1)
            : (secondary.videoWidth || state.project.secondary_video?.width || 1),
        );
        const secondaryHeight = Math.max(
          1,
          imageSecondary
            ? (secondaryImage.naturalHeight || state.project.secondary_video?.height || 1)
            : (secondary.videoHeight || state.project.secondary_video?.height || 1),
        );
        if (
          (merge.layout === "pip" && frameRect)
          || merge.layout === "full_screen_portrait"
        ) {
          const activeSource = mergeSources[0] || null;
          const previewRect =
            merge.layout === "full_screen_portrait"
              ? {
                  left: 0,
                  top: 0,
                  width: Math.max(1, stage.clientWidth || video.clientWidth || 1),
                  height: Math.max(1, stage.clientHeight || video.clientHeight || 1),
                }
              : frameRect;
          const rect = activeSource
            ? mergeSourcePipRect(activeSource, previewRect, pipSizeValue)
            : (() => {
                let insetWidth = Math.max(1, Math.round(previewRect.width * (pipSizeValue / 100)));
                let insetHeight = Math.max(1, Math.round((secondaryHeight / secondaryWidth) * insetWidth));
                if (insetHeight > previewRect.height) {
                  const fitScale = previewRect.height / insetHeight;
                  insetWidth = Math.max(1, Math.round(insetWidth * fitScale));
                  insetHeight = Math.max(1, Math.round(insetHeight * fitScale));
                }
                const travelX = Math.max(0, previewRect.width - insetWidth);
                const travelY = Math.max(0, previewRect.height - insetHeight);
                return {
                  left: previewRect.left + (travelX * (normalizedCoordinateValue(merge.pip_x) ?? 1)),
                  top: previewRect.top + (travelY * (normalizedCoordinateValue(merge.pip_y) ?? 1)),
                  width: insetWidth,
                  height: insetHeight,
                };
              })();
          activeSecondary.style.position = "absolute";
          activeSecondary.style.left = `${rect.left}px`;
          activeSecondary.style.top = `${rect.top}px`;
          activeSecondary.style.width = `${rect.width}px`;
          activeSecondary.style.height = `${rect.height}px`;
          activeSecondary.style.maxWidth = `${rect.width}px`;
          activeSecondary.style.maxHeight = `${rect.height}px`;
          activeSecondary.style.zIndex = "1";
        }
      }
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
