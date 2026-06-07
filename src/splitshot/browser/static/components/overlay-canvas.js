export function createOverlayCanvasComponent({
  $ = (id) => document.getElementById(id),
  windowObject = window,
  getState = () => null,
  getSelectedShotId = () => null,
  getOverlayFrame = () => null,
  setOverlayFrame = () => {},
  getOverlayFrameMode = () => null,
  setOverlayFrameMode = () => {},
  activity = () => {},
  scheduleSecondaryPreviewSync = () => {},
  renderStageCompositor = () => {},
  renderLiveOverlay = () => {},
  renderWaveformPlayhead = () => {},
  currentPrimaryVideoPositionMs = () => 0,
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function requestOverlayFrame(video, tick) {
    if (!(video instanceof HTMLVideoElement)) return;
    if (typeof video.requestVideoFrameCallback === "function") {
      setOverlayFrameMode("video-frame");
      setOverlayFrame(video.requestVideoFrameCallback(tick));
      return;
    }
    setOverlayFrameMode("animation-frame");
    setOverlayFrame(windowObject.requestAnimationFrame((now) => tick(now, null)));
  }

  function cancelOverlayFrame(video) {
    const overlayFrame = getOverlayFrame();
    if (overlayFrame === null) return;
    if (getOverlayFrameMode() === "video-frame" && typeof video?.cancelVideoFrameCallback === "function") {
      video.cancelVideoFrameCallback(overlayFrame);
    } else {
      windowObject.cancelAnimationFrame(overlayFrame);
    }
    setOverlayFrame(null);
    setOverlayFrameMode(null);
  }

  function startOverlayLoop() {
    const video = $("primary-video");
    if (!(video instanceof HTMLVideoElement) || getOverlayFrame() !== null) return;
    activity("video.play", { current_time_s: video.currentTime });
    scheduleSecondaryPreviewSync();
    const tick = (_now, metadata = null) => {
      setOverlayFrame(null);
      setOverlayFrameMode(null);
      const mediaTimeS = Number.isFinite(metadata?.mediaTime) ? metadata.mediaTime : null;
      activity("frame.overlay", {
        current_time_s: mediaTimeS ?? video.currentTime,
        frame_source: mediaTimeS === null ? "animation-frame" : "video-frame",
        merge_sources: (currentState()?.project?.merge_sources || []).length,
        selected_shot_id: getSelectedShotId() || "",
      });
      renderStageCompositor(video);
      scheduleSecondaryPreviewSync();
      renderLiveOverlay(mediaTimeS === null ? null : mediaTimeS * 1000);
      renderWaveformPlayhead(mediaTimeS === null ? currentPrimaryVideoPositionMs() : mediaTimeS * 1000);
      if (video.paused || video.ended) return;
      requestOverlayFrame(video, tick);
    };
    requestOverlayFrame(video, tick);
  }

  function stopOverlayLoop() {
    const video = $("primary-video");
    if (!(video instanceof HTMLVideoElement) || getOverlayFrame() === null) return;
    activity("video.pause", { current_time_s: video.currentTime });
    cancelOverlayFrame(video);
    scheduleSecondaryPreviewSync();
    renderLiveOverlay();
    renderWaveformPlayhead();
  }

  return Object.freeze({
    requestOverlayFrame,
    cancelOverlayFrame,
    startOverlayLoop,
    stopOverlayLoop,
  });
}
