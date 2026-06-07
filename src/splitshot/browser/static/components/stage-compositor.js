export function createStageCompositorComponent({
  $ = (id) => document.getElementById(id),
  windowObject = window,
  activity = () => {},
  getState = () => null,
  sourceIdentifier = (source, fallback = "") => source?.id || source?.asset?.id || fallback,
  resolvedMergePreviewSource = (source) => ({
    mediaUrl: "",
    mediaKind: source?.asset?.is_still_image ? "image" : "video",
    effectivePath: source?.asset?.path || "",
    usesDerivative: false,
  }),
  resolveMergePreviewScene = () => null,
  mergePreviewTargetTime = (primaryTimeS) => Math.max(0, Number(primaryTimeS || 0)),
  syncPreviewPlaybackToTarget = () => "noop",
} = {}) {
  const mediaPool = new Map();

  function currentState() {
    return getState() || {};
  }

  function compositorCanvas() {
    return $("stage-compositor-canvas");
  }

  function pausePooledVideo(entry) {
    if (!(entry?.media instanceof HTMLVideoElement)) return;
    if (!entry.media.paused) entry.media.pause();
  }

  function removePoolEntry(sourceId) {
    const entry = mediaPool.get(sourceId);
    if (!entry) return;
    pausePooledVideo(entry);
    entry.media.removeAttribute?.("src");
    mediaPool.delete(sourceId);
  }

  function clearCanvas() {
    const canvas = compositorCanvas();
    if (!(canvas instanceof HTMLCanvasElement)) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    canvas.hidden = true;
  }

  function stop() {
    mediaPool.forEach((entry) => pausePooledVideo(entry));
    clearCanvas();
  }

  function syncCanvasSize(canvas, stage) {
    const width = Math.max(1, Math.round(stage?.clientWidth || canvas.clientWidth || 1));
    const height = Math.max(1, Math.round(stage?.clientHeight || canvas.clientHeight || 1));
    if (canvas.width !== width) canvas.width = width;
    if (canvas.height !== height) canvas.height = height;
    return { width, height };
  }

  function ensureMediaEntry(source, sceneItem) {
    const sourceId = sceneItem.sourceId || sourceIdentifier(source);
    if (!sourceId) return null;
    const resolved = resolvedMergePreviewSource(source);
    let entry = mediaPool.get(sourceId) || null;
    const desiredKind = resolved.mediaKind === "image" ? "image" : "video";
    if (!entry || entry.kind !== desiredKind) {
      if (entry) removePoolEntry(sourceId);
      const media = desiredKind === "image" ? new Image() : document.createElement("video");
      if (media instanceof HTMLVideoElement) {
        media.defaultMuted = true;
        media.muted = true;
        media.volume = 0;
        media.playsInline = true;
        media.preload = "auto";
        media.disablePictureInPicture = true;
        media.crossOrigin = "anonymous";
      } else {
        media.decoding = "async";
        media.crossOrigin = "anonymous";
      }
      entry = {
        kind: desiredKind,
        media,
        mediaUrl: "",
        effectivePath: "",
      };
      mediaPool.set(sourceId, entry);
    }
    if (entry.mediaUrl !== resolved.mediaUrl || entry.effectivePath !== resolved.effectivePath) {
      entry.mediaUrl = resolved.mediaUrl;
      entry.effectivePath = resolved.effectivePath;
      if (entry.media instanceof HTMLImageElement) {
        entry.media.src = resolved.mediaUrl;
      } else if (entry.media instanceof HTMLVideoElement) {
        pausePooledVideo(entry);
        entry.media.dataset.sourcePath = resolved.effectivePath;
        entry.media.dataset.mediaUrl = resolved.mediaUrl;
        entry.media.src = resolved.mediaUrl;
        entry.media.load();
      }
    }
    return entry;
  }

  function drawScene(canvas, scene) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!scene || !Array.isArray(scene.items) || scene.items.length === 0) {
      canvas.hidden = true;
      return;
    }
    canvas.hidden = false;
    const stageRect = scene.stageRect || { left: 0, top: 0, width: canvas.width, height: canvas.height };
    scene.items
      .slice()
      .sort((left, right) => Number(left.zIndex || 0) - Number(right.zIndex || 0))
      .forEach((item) => {
        const entry = mediaPool.get(item.sourceId);
        const media = entry?.media;
        if (!(media instanceof HTMLImageElement || media instanceof HTMLVideoElement)) return;
        if (media instanceof HTMLVideoElement && media.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
        if (media instanceof HTMLImageElement && !media.complete) return;
        const left = Number(item.rect?.left || 0) - Number(stageRect.left || 0);
        const top = Number(item.rect?.top || 0) - Number(stageRect.top || 0);
        const width = Number(item.rect?.width || 0);
        const height = Number(item.rect?.height || 0);
        if (width <= 0 || height <= 0) return;
        ctx.save();
        ctx.globalAlpha = Math.max(0, Math.min(1, Number(item.opacity ?? 1)));
        ctx.drawImage(media, left, top, width, height);
        ctx.restore();
      });
  }

  function syncVideoEntry(entry, sceneItem, primary) {
    if (!(entry?.media instanceof HTMLVideoElement) || !(primary instanceof HTMLVideoElement)) return "noop";
    const target = mergePreviewTargetTime(primary.currentTime, sceneItem.source);
    const targetPlaybackRate = Number(primary.playbackRate || 1) || 1;
    const status = syncPreviewPlaybackToTarget(entry.media, target, targetPlaybackRate, primary.paused);
    if (primary.paused) {
      pausePooledVideo(entry);
      return status;
    }
    if (entry.media.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return status;
    if (entry.media.paused) {
      entry.media.play().catch((error) => {
        activity("video.stage_compositor.error", {
          source_id: sceneItem.sourceId,
          name: error?.name || "Error",
          error: error?.message || String(error || "Unknown error"),
          status,
        });
      });
    }
    return status;
  }

  function syncAndRender(primary, {
    video = null,
    stage = null,
    pipSizeValue = null,
  } = {}) {
    const canvas = compositorCanvas();
    if (!(canvas instanceof HTMLCanvasElement) || !(primary instanceof HTMLVideoElement)) return null;
    const stageElement = stage || $("video-stage");
    const videoElement = video || $("primary-video");
    if (!(stageElement instanceof HTMLElement) || !(videoElement instanceof HTMLVideoElement)) {
      clearCanvas();
      return null;
    }
    const mergeSources = currentState()?.project?.merge_sources || [];
    const scene = resolveMergePreviewScene(videoElement, stageElement, mergeSources, pipSizeValue);
    const sceneItems = Array.isArray(scene?.items) ? scene.items : [];
    if (!scene || sceneItems.length === 0) {
      stop();
      return scene;
    }

    const expectedIds = new Set(sceneItems.map((item) => item.sourceId));
    [...mediaPool.keys()].forEach((sourceId) => {
      if (!expectedIds.has(sourceId)) removePoolEntry(sourceId);
    });

    const syncStatuses = [];
    sceneItems.forEach((item) => {
      const entry = ensureMediaEntry(item.source, item);
      if (!entry) return;
      if (entry.media instanceof HTMLVideoElement) {
        syncStatuses.push({
          sourceId: item.sourceId,
          status: syncVideoEntry(entry, item, primary),
        });
      }
    });

    syncCanvasSize(canvas, stageElement);
    drawScene(canvas, scene);
    return { scene, syncStatuses };
  }

  function debugSnapshot(primary, {
    video = null,
    stage = null,
    pipSizeValue = null,
  } = {}) {
    const stageElement = stage || $("video-stage");
    const videoElement = video || $("primary-video");
    const scene = resolveMergePreviewScene(videoElement, stageElement, currentState()?.project?.merge_sources || [], pipSizeValue);
    return {
      canvasHidden: !(compositorCanvas() instanceof HTMLCanvasElement) || compositorCanvas().hidden,
      items: (scene?.items || []).map((item) => {
        const entry = mediaPool.get(item.sourceId);
        const media = entry?.media;
        return {
          sourceId: item.sourceId,
          mediaKind: item.resolved?.mediaKind || item.source?.asset?.media_kind || "video",
          effectivePath: item.resolved?.effectivePath || "",
          mediaUrl: item.resolved?.mediaUrl || "",
          targetTime: mergePreviewTargetTime(primary?.currentTime || 0, item.source),
          currentTime: media instanceof HTMLMediaElement ? Number(media.currentTime || 0) : null,
          paused: media instanceof HTMLMediaElement ? media.paused : null,
          readyState: media instanceof HTMLMediaElement ? media.readyState : null,
          playbackRate: media instanceof HTMLMediaElement ? Number(media.playbackRate || 1) : null,
          rect: item.rect,
        };
      }),
    };
  }

  return Object.freeze({
    clearCanvas,
    debugSnapshot,
    stop,
    syncAndRender,
  });
}
