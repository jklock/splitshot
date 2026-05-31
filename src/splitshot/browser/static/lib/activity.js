function emitBackbone(backbone, eventName, detail = undefined) {
  backbone?.bus?.emit?.(eventName, detail);
  return detail;
}

function patchBackboneStore(backbone, patch = {}) {
  if (!backbone?.storePatch || !patch || typeof patch !== "object") return patch;
  backbone.storePatch(patch);
  return patch;
}

export function createActivityRuntime({
  backbone = null,
  runtime,
  renderExportLog = () => {},
  setProcessingProgress = () => {},
  ACTIVITY_FLUSH_DELAY_MS = 160,
  ACTIVITY_BATCH_SIZE = 48,
  ACTIVITY_POLL_INTERVAL_MS = 1000,
} = {}) {
  function syncActivityBackbone() {
    patchBackboneStore(backbone, {
      activityCursor: Number(runtime?.activityCursor || 0),
      activityQueueLength: Array.isArray(runtime?.activityQueue) ? runtime.activityQueue.length : 0,
      exportLogLineCount: Array.isArray(runtime?.exportLogLines) ? runtime.exportLogLines.length : 0,
    });
  }

  function flushActivityQueue() {
    if (runtime.activityFlushTimer !== null) {
      window.clearTimeout(runtime.activityFlushTimer);
      runtime.activityFlushTimer = null;
    }
    if (runtime.activityQueue.length === 0) return;
    const entries = runtime.activityQueue;
    runtime.activityQueue = [];
    syncActivityBackbone();
    emitBackbone(backbone, "activity.flush", { entries });
    fetch("/api/activity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries }),
      keepalive: true,
    }).catch((error) => {
      console.warn("[splitshot] activity log failed", error);
    });
  }

  function queueActivity(event, detail = {}) {
    const entry = { event, detail, ts: new Date().toISOString() };
    runtime.activityQueue.push(entry);
    syncActivityBackbone();
    emitBackbone(backbone, "activity.queue", entry);
    if (runtime.activityQueue.length >= ACTIVITY_BATCH_SIZE) {
      flushActivityQueue();
      return;
    }
    if (runtime.activityFlushTimer !== null) return;
    runtime.activityFlushTimer = window.setTimeout(() => {
      runtime.activityFlushTimer = null;
      flushActivityQueue();
    }, ACTIVITY_FLUSH_DELAY_MS);
  }

  function activity(event, detail = {}) {
    console.info("[splitshot]", event, detail);
    emitBackbone(backbone, "activity.emit", { event, detail });
    queueActivity(event, detail);
  }

  function clearActivityPollTimer() {
    if (runtime.activityPollTimer === null) return;
    window.clearTimeout(runtime.activityPollTimer);
    runtime.activityPollTimer = null;
  }

  function clearActivityEventSource() {
    const eventSource = runtime.activityEventSource;
    if (!eventSource) return;
    try {
      eventSource.close();
    } catch {}
    runtime.activityEventSource = null;
  }

  function appendExportLogLine(line) {
    const nextLine = String(line || "").trimEnd();
    if (!nextLine) return;
    runtime.exportLogLines.push(nextLine);
    runtime.exportLogLines = runtime.exportLogLines.slice(-500);
    syncActivityBackbone();
  }

  function clearCurrentExportLogState() {
    runtime.exportLogLines = [];
    if (runtime.state?.project?.export) {
      runtime.state.project.export.last_log = "";
      runtime.state.project.export.last_error = null;
    }
    syncActivityBackbone();
    renderExportLog();
  }

  function consumeActivityEntries(entries = []) {
    let exportLogChanged = false;
    entries.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const seq = Number(entry.seq || 0);
      if (seq > runtime.activityCursor) runtime.activityCursor = seq;
      const eventName = String(entry.event_type || entry.event || "");
      const detail = entry.detail && typeof entry.detail === "object"
        ? entry.detail
        : entry.payload && typeof entry.payload === "object"
          ? entry.payload
          : {};
      if (eventName === "/api/activity/poll") return;
      if (eventName === "api.export.log") {
        appendExportLogLine(entry.line);
        exportLogChanged = true;
        return;
      }
      if (eventName === "api.export.progress") {
        const nextProgress = Number(entry.progress);
        if (Number.isFinite(nextProgress)) {
          setProcessingProgress(nextProgress * 100);
          exportLogChanged = true;
        }
        return;
      }
      if (eventName === "api.export.complete") {
        setProcessingProgress(100);
        exportLogChanged = true;
        return;
      }
      if (eventName === "job.log" && detail.legacy_event === "api.export.log") {
        appendExportLogLine(detail.line || entry.message || "");
        exportLogChanged = true;
        return;
      }
      if (eventName === "job.progress" && detail.legacy_event === "api.export.progress") {
        const nextProgress = Number(entry.progress_percent);
        if (Number.isFinite(nextProgress)) {
          setProcessingProgress(nextProgress);
          exportLogChanged = true;
        }
        return;
      }
      if (eventName === "job.completed" && detail.result?.legacy_event === "api.export.complete") {
        setProcessingProgress(100);
        exportLogChanged = true;
      }
    });
    syncActivityBackbone();
    if (exportLogChanged) renderExportLog();
  }

  async function runActivityPoll() {
    clearActivityPollTimer();
    try {
      const response = await fetch(`/api/activity/poll?after=${runtime.activityCursor}`);
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || response.statusText);
      consumeActivityEntries(Array.isArray(data.entries) ? data.entries : []);
      runtime.activityCursor = Math.max(runtime.activityCursor, Number(data.cursor || 0));
      syncActivityBackbone();
      emitBackbone(backbone, "activity.poll", {
        cursor: runtime.activityCursor,
        count: Array.isArray(data.entries) ? data.entries.length : 0,
      });
    } catch (error) {
      console.warn("[splitshot] activity poll failed", error);
    } finally {
      runtime.activityPollTimer = window.setTimeout(runActivityPoll, ACTIVITY_POLL_INTERVAL_MS);
    }
  }

  function startActivityStream() {
    if (runtime.activityEventSource) return true;
    if (typeof window.EventSource !== "function") return false;
    try {
      const eventSource = new window.EventSource(`/api/events?after=${runtime.activityCursor}`);
      runtime.activityEventSource = eventSource;
      const handleEvent = (event) => {
        try {
          const payload = JSON.parse(event.data || "{}");
          consumeActivityEntries([payload]);
        } catch (error) {
          console.warn("[splitshot] activity stream payload failed", error);
        }
      };
      [
        "message",
        "job.queued",
        "job.started",
        "job.progress",
        "job.log",
        "job.completed",
        "job.failed",
        "job.canceled",
        "runtime.health",
      ].forEach((eventName) => {
        eventSource.addEventListener(eventName, handleEvent);
      });
      eventSource.onerror = () => {
        emitBackbone(backbone, "activity.stream.error", { cursor: runtime.activityCursor });
        clearActivityEventSource();
        runtime.activityPollTimer = window.setTimeout(runActivityPoll, ACTIVITY_POLL_INTERVAL_MS);
      };
      emitBackbone(backbone, "activity.stream.start", { cursor: runtime.activityCursor });
      return true;
    } catch (error) {
      console.warn("[splitshot] activity stream failed", error);
      clearActivityEventSource();
      return false;
    }
  }

  function startActivityPolling() {
    if (runtime.activityPollTimer !== null || runtime.activityEventSource) return;
    if (startActivityStream()) return;
    runtime.activityPollTimer = window.setTimeout(runActivityPoll, 0);
  }

  function stopActivityPolling() {
    clearActivityPollTimer();
    clearActivityEventSource();
  }

  function buttonDescriptor(button) {
    return {
      id: button.id || "",
      text: button.textContent.trim().replace(/\s+/g, " "),
      tool: button.dataset.tool || "",
      waveform_mode: button.dataset.waveformMode || "",
      nudge_ms: button.dataset.nudge || "",
      sync_ms: button.dataset.sync || "",
      opens_media: button.hasAttribute("data-open-merge-media"),
    };
  }

  function wireGlobalActivityLogging() {
    document.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      const button = event.target.closest("button");
      if (!button) return;
      activity("button.click", buttonDescriptor(button));
    }, true);
    document.addEventListener("change", (event) => {
      if (!(event.target instanceof HTMLElement)) return;
      const control = event.target;
      if (!["INPUT", "SELECT", "TEXTAREA"].includes(control.tagName)) return;
      activity("control.change", {
        id: control.id || "",
        name: control.name || "",
        type: control.type || control.tagName.toLowerCase(),
        value: control.type === "file" ? Array.from(control.files || []).map((file) => file.name) : control.value,
      });
    }, true);
    document.addEventListener("input", (event) => {
      if (!(event.target instanceof HTMLElement)) return;
      const control = event.target;
      if (!["INPUT", "TEXTAREA"].includes(control.tagName)) return;
      if (control.type === "file") return;
      activity("control.input", {
        id: control.id || "",
        name: control.name || "",
        type: control.type || control.tagName.toLowerCase(),
        value: control.value,
      });
    }, true);
  }

  syncActivityBackbone();

  return Object.freeze({
    flushActivityQueue,
    queueActivity,
    activity,
    clearActivityPollTimer,
    clearActivityEventSource,
    appendExportLogLine,
    clearCurrentExportLogState,
    consumeActivityEntries,
    runActivityPoll,
    startActivityStream,
    startActivityPolling,
    stopActivityPolling,
    buttonDescriptor,
    wireGlobalActivityLogging,
  });
}
