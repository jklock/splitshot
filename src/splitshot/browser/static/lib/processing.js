function emitBackbone(backbone, eventName, detail = undefined) {
  backbone?.bus?.emit?.(eventName, detail);
  return detail;
}

function patchBackboneStore(backbone, patch = {}) {
  if (!backbone?.storePatch || !patch || typeof patch !== "object") return patch;
  backbone.storePatch(patch);
  return patch;
}

export function createProcessingRuntime({
  backbone = null,
  runtime,
  $,
  clampNumber,
  clearCurrentExportLogState = () => {},
  activity = () => {},
  PROCESSING_BAR_SHOW_DELAY_MS = 180,
  PROCESSING_BAR_MIN_VISIBLE_MS = 320,
} = {}) {
  function syncProcessingBackbone() {
    patchBackboneStore(backbone, {
      busyCount: Number(runtime?.busyCount || 0),
      processingProgressPercent: Number(runtime?.processingProgressPercent || 0),
      activeProcessingPath: runtime?.activeProcessingPath || null,
    });
  }

  function nowMs() {
    return window.performance?.now?.() ?? Date.now();
  }

  function clearProcessingBarShowTimer() {
    if (runtime.processingBarShowTimer === null) return;
    window.clearTimeout(runtime.processingBarShowTimer);
    runtime.processingBarShowTimer = null;
  }

  function clearProcessingBarHideTimer() {
    if (runtime.processingBarHideTimer === null) return;
    window.clearTimeout(runtime.processingBarHideTimer);
    runtime.processingBarHideTimer = null;
  }

  function clearProcessingProgressTimer() {
    if (runtime.processingProgressTimer === null) return;
    window.clearInterval(runtime.processingProgressTimer);
    runtime.processingProgressTimer = null;
  }

  function setProcessingProgress(percent, options = {}) {
    const allowDecrease = Boolean(options.allowDecrease);
    const nextPercent = clampNumber(Number(percent) || 0, 0, 100);
    runtime.processingProgressPercent = allowDecrease
      ? nextPercent
      : Math.max(runtime.processingProgressPercent, nextPercent);
    const fill = $("processing-progress-fill");
    const label = $("processing-percent");
    if (fill) fill.style.width = `${runtime.processingProgressPercent}%`;
    if (label) label.textContent = `${Math.round(runtime.processingProgressPercent)}%`;
    syncProcessingBackbone();
    return runtime.processingProgressPercent;
  }

  function progressProfileForPath(path) {
    if (path === "/api/export") return { ceiling: 99, step: 4 };
    if (
      path === "/api/files/practiscore"
      || path === "/api/import/practiscore"
      || path === "/api/project/practiscore"
    ) return { ceiling: 95, step: 15 };
    if (path === "/api/project/save") return { ceiling: 92, step: 18 };
    if (path === "/api/import/primary" || path === "/api/files/primary") return { ceiling: 95, step: 12 };
    if (path === "/api/import/secondary" || path === "/api/import/merge" || path === "/api/files/merge") {
      return { ceiling: 95, step: 16 };
    }
    return { ceiling: 90, step: 20 };
  }

  function startProcessingProgress(path) {
    runtime.activeProcessingPath = path;
    clearProcessingProgressTimer();
    setProcessingProgress(0, { allowDecrease: true });
    if (path === "/api/export") return;
    const profile = progressProfileForPath(path);
    runtime.processingProgressTimer = window.setInterval(() => {
      const next = Math.min(profile.ceiling, runtime.processingProgressPercent + profile.step);
      if (next !== runtime.processingProgressPercent) setProcessingProgress(next);
    }, 1000);
    syncProcessingBackbone();
  }

  function stopProcessingProgress(finalPercent = 100) {
    clearProcessingProgressTimer();
    runtime.activeProcessingPath = null;
    setProcessingProgress(finalPercent, { allowDecrease: true });
    syncProcessingBackbone();
  }

  function hideProcessingBarNow(finalMessage = "Ready.") {
    const bar = $("processing-bar");
    clearProcessingBarShowTimer();
    clearProcessingBarHideTimer();
    clearProcessingProgressTimer();
    runtime.processingBarVisibleAtMs = 0;
    $("processing-message").textContent = finalMessage;
    $("processing-detail").textContent = "Ready";
    setProcessingProgress(0, { allowDecrease: true });
    bar.hidden = true;
    syncProcessingBackbone();
  }

  function scheduleProcessingBarShow(message, detail) {
    const bar = $("processing-bar");
    clearProcessingBarHideTimer();
    $("processing-message").textContent = message;
    $("processing-detail").textContent = detail;
    if (!bar.hidden) return;
    clearProcessingBarShowTimer();
    runtime.processingBarShowTimer = window.setTimeout(() => {
      runtime.processingBarShowTimer = null;
      if (runtime.busyCount <= 0) return;
      bar.hidden = false;
      runtime.processingBarVisibleAtMs = nowMs();
    }, PROCESSING_BAR_SHOW_DELAY_MS);
  }

  function scheduleProcessingBarHide(finalMessage = "Ready.") {
    clearProcessingBarShowTimer();
    clearProcessingBarHideTimer();
    const bar = $("processing-bar");
    $("processing-message").textContent = finalMessage;
    $("processing-detail").textContent = "Ready";
    if (bar.hidden) return;
    const remainingMs = Math.max(0, PROCESSING_BAR_MIN_VISIBLE_MS - (nowMs() - runtime.processingBarVisibleAtMs));
    runtime.processingBarHideTimer = window.setTimeout(() => {
      runtime.processingBarHideTimer = null;
      if (runtime.busyCount !== 0) return;
      hideProcessingBarNow(finalMessage);
    }, remainingMs);
  }

  function forceHideProcessingBar(finalMessage = "Ready.") {
    runtime.busyCount = 0;
    syncProcessingBackbone();
    hideProcessingBarNow(finalMessage);
  }

  function beginProcessing(message, detail = "Working locally", path = null) {
    runtime.busyCount += 1;
    syncProcessingBackbone();
    if (path === "/api/export") {
      clearCurrentExportLogState();
    }
    if (runtime.busyCount === 1) startProcessingProgress(path);
    scheduleProcessingBarShow(message, detail);
    emitBackbone(backbone, "processing.start", { message, detail, path, busy_count: runtime.busyCount });
    activity("ui.processing.start", { message, detail, busy_count: runtime.busyCount });
    return (finalMessage = "Ready.") => {
      runtime.busyCount = Math.max(0, runtime.busyCount - 1);
      syncProcessingBackbone();
      emitBackbone(backbone, "processing.finish", { message: finalMessage, path, busy_count: runtime.busyCount });
      activity("ui.processing.finish", { message: finalMessage, busy_count: runtime.busyCount });
      if (runtime.busyCount === 0) {
        stopProcessingProgress(100);
        scheduleProcessingBarHide(finalMessage);
      }
    };
  }

  function processingForPath(path, payload = null) {
    if (path === "/api/export") return { message: "Exporting video...", detail: "Running FFmpeg locally" };
    if (path === "/api/practiscore/dashboard/open") {
      return { message: "Opening PractiScore dashboard...", detail: "Launching PractiScore in your system browser" };
    }
    if (path === "/api/import/primary") {
      return { message: "Analyzing primary video...", detail: "Copying into project Input, then detecting beep and shots" };
    }
    if (path === "/api/import/practiscore") {
      return { message: "Importing PractiScore results...", detail: "Copying into project CSV and building stages" };
    }
    if (path === "/api/project/stage/import-primary") {
      return { message: "Importing primary media...", detail: "Copying into project Input and analyzing locally" };
    }
    if (path === "/api/project/stage/import-added") {
      return { message: "Importing added media...", detail: "Copying into project Input" };
    }
    if (
      (path === "/api/analysis/threshold" || (path === "/api/analysis/shotml-settings" && payload?.rerun))
      && runtime.state?.project?.primary_video?.path
    ) {
      return { message: "Re-running ShotML...", detail: "Refreshing shot detections with the current settings" };
    }
    if (path === "/api/import/merge" || path === "/api/files/merge") {
      return { message: "Importing media...", detail: "Copying into project Input and adding media" };
    }
    if (path === "/api/import/secondary") {
      return { message: "Importing media...", detail: "Copying into project Input and adding media" };
    }
    if (path === "/api/merge/source/trim-all") {
      return { message: "Trimming added media...", detail: "Writing derivative files and refreshing waveform state" };
    }
    if (path === "/api/merge/source/trim") {
      return { message: "Trimming source...", detail: "Writing a derivative file and refreshing preview state" };
    }
    if (path === "/api/project/details") return { message: "Updating project details...", detail: "Saving metadata locally" };
    if (path === "/api/project/practiscore") return { message: "Updating match import settings...", detail: "Saving stage and competitor details" };
    if (path === "/api/project/open") return { message: "Opening project folder...", detail: "Loading project.json and local assets" };
    if (path === "/api/project/reveal") return { message: "Opening project folder...", detail: "Showing the project in your file browser" };
    if (path === "/api/project/save") return { message: "Updating project folder...", detail: "Writing project.json metadata" };
    if (path === "/api/project/delete") return { message: "Deleting project folder...", detail: "Removing the project folder from disk" };
    if (path === "/api/project/new") return { message: "Creating new project...", detail: "Resetting project state" };
    return null;
  }

  syncProcessingBackbone();

  return Object.freeze({
    clearProcessingBarShowTimer,
    clearProcessingBarHideTimer,
    clearProcessingProgressTimer,
    setProcessingProgress,
    progressProfileForPath,
    startProcessingProgress,
    stopProcessingProgress,
    hideProcessingBarNow,
    scheduleProcessingBarShow,
    scheduleProcessingBarHide,
    forceHideProcessingBar,
    beginProcessing,
    processingForPath,
  });
}
