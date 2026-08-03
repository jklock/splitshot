function emitBackbone(backbone, eventName, detail = undefined) {
  backbone?.bus?.emit?.(eventName, detail);
  return detail;
}

function patchBackboneStore(backbone, patch = {}) {
  if (!backbone?.storePatch || !patch || typeof patch !== "object") return patch;
  backbone.storePatch(patch);
  return patch;
}

export function createApiRuntime({
  backbone = null,
  runtime,
  processingForPath = () => null,
  requestRender = () => {},
  activity = () => {},
  beginProcessing = () => null,
  forceHideProcessingBar = () => {},
  setStatus = () => {},
  mergeProjectUiState = (remoteUiState) => remoteUiState,
  normalizeProjectUiState = (uiState) => uiState,
  shotSelectionContext = () => null,
  resolveSelectedShotId = (_nextState, requestedShotId = null) => requestedShotId,
  mergeProjectDetailsDraft = () => {},
  mergeMergeDraft = () => {},
  mergeOverlayPositionDraft = () => {},
  mergeOverlayStyleDraft = () => {},
  mergeOverlayTextBoxesDraft = () => {},
  applyPopupDraft = () => {},
  mergePopupDraft = () => {},
  mergeExportDraft = () => {},
  setStateValue = () => {},
  applyProjectUiState = () => {},
  syncSelectedShotId = () => {},
  syncLocalProjectUiState = () => {},
  resetLocalProjectView = () => {},
  readProjectUiStatePayload = () => ({}),
} = {}) {
  function syncApiBackbone() {
    patchBackboneStore(backbone, {
      currentProjectId: runtime?.currentProjectId || null,
      initialProjectUiStateApplied: Boolean(runtime?.initialProjectUiStateApplied),
      pendingBootstrapProjectUiStateOverride: Boolean(runtime?.pendingBootstrapProjectUiStateOverride),
    });
  }

  function hasCompleteProjectState(nextState) {
    return Boolean(
      nextState?.project?.analysis
        && nextState?.project?.overlay
        && nextState?.project?.merge
        && nextState?.project?.export
        && nextState?.project?.ui_state
        && nextState?.metrics
        && nextState?.media,
    );
  }

  function stateHasShot(nextState, shotId) {
    return Boolean(shotId)
      && (nextState?.project?.analysis?.shots || []).some((shot) => shot.id === shotId);
  }

  function apiRequestDomain(path) {
    const normalizedPath = String(path || "");
    if (normalizedPath === "/api/popups") return "popups";
    if (normalizedPath === "/api/overlay") return "overlay";
    if (normalizedPath === "/api/merge" || normalizedPath.startsWith("/api/merge/")) return "merge";
    if (normalizedPath === "/api/export/preset" || normalizedPath === "/api/export/settings") {
      return "export.settings";
    }
    if (normalizedPath === "/api/project/details") return "project.details";
    if (normalizedPath === "/api/project/practiscore") return "project.practiscore";
    if (normalizedPath === "/api/project/ui-state") return "project.ui-state";
    if (normalizedPath === "/api/analysis/threshold" || normalizedPath === "/api/analysis/shotml-settings") {
      return "analysis.shotml";
    }
    if (normalizedPath === "/api/scoring" || normalizedPath.startsWith("/api/scoring/")) return "scoring";
    if (normalizedPath.startsWith("/api/shots/")) return "shots";
    return normalizedPath;
  }

  function apiResponseOwnsRemoteState(path) {
    const normalizedPath = String(path || "");
    if (normalizedPath === "/api/project/ui-state") return false;
    return true;
  }

  function apiResponseNeedsRender(path) {
    const normalizedPath = String(path || "");
    // These routes commit state that the client has already rendered
    // optimistically. Rendering their responses again replaces active marker
    // and drag nodes during an ordinary save.
    return normalizedPath !== "/api/project/ui-state"
      && normalizedPath !== "/api/popups";
  }

  async function parseJsonResponse(response, path) {
    const contentType = String(response.headers.get("content-type") || "").toLowerCase();
    const bodyText = await response.text();
    if (!contentType.includes("application/json")) {
      const preview = bodyText.trim().slice(0, 120) || "<empty>";
      throw new Error(`Expected JSON from ${path}, got ${contentType || "unknown"}: ${preview}`);
    }
    try {
      return JSON.parse(bodyText);
    } catch (error) {
      throw new Error(`Invalid JSON from ${path}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  let apiRequestSequence = 0;
  const latestApiRequestSequenceByDomain = new Map();
  let latestRemoteStateRequestSequence = 0;

  function beginTrackedApiRequest(path) {
    const domain = apiRequestDomain(path);
    apiRequestSequence += 1;
    const request = { path, domain, sequence: apiRequestSequence };
    latestApiRequestSequenceByDomain.set(domain, request.sequence);
    if (apiResponseOwnsRemoteState(path)) latestRemoteStateRequestSequence = request.sequence;
    return request;
  }

  function isTrackedApiRequestStale(request) {
    if (!request) return false;
    if (latestApiRequestSequenceByDomain.get(request.domain) !== request.sequence) return true;
    return apiResponseOwnsRemoteState(request.path)
      && request.sequence !== latestRemoteStateRequestSequence;
  }

  async function api(path, payload = null) {
    const request = beginTrackedApiRequest(path);
    if (path === "/api/popups" && payload && typeof payload === "object") applyPopupDraft(payload);
    emitBackbone(backbone, "api.request", { path, payload });
    activity("api.request", { path, payload });
    const processing = processingForPath(path, payload);
    const finishProcessing = payload === null || processing === null
      ? null
      : beginProcessing(processing.message, processing.detail, path);
    const options = payload === null
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        };
    try {
      const response = await fetch(path, options);
      const data = await parseJsonResponse(response, path);
      if (isTrackedApiRequestStale(request)) {
        const responseDetail = {
          path,
          status: data?.status,
          shots: data?.metrics?.total_shots,
          stale: true,
          domain: request.domain,
        };
        emitBackbone(backbone, "api.response", responseDetail);
        activity("api.response", responseDetail);
        if (finishProcessing) finishProcessing(data?.status || "Ready.");
        return null;
      }
      if (!response.ok || data.error) throw new Error(data.error || response.statusText);
      if (apiResponseOwnsRemoteState(path)) {
        applyRemoteState(data, { preserveActiveInteraction: !apiResponseNeedsRender(path) });
      }
      if (finishProcessing) finishProcessing(data.status || "Ready.");
      if (apiResponseNeedsRender(path)) requestRender();
      emitBackbone(backbone, "api.response", { path, status: data.status, shots: data.metrics?.total_shots });
      activity("api.response", { path, status: data.status, shots: data.metrics?.total_shots });
      return data;
    } catch (error) {
      if (isTrackedApiRequestStale(request)) {
        const errorDetail = {
          path,
          error: error?.message || String(error),
          stale: true,
          domain: request.domain,
        };
        emitBackbone(backbone, "api.error", errorDetail);
        activity("api.error", errorDetail);
        if (finishProcessing) finishProcessing("Ready.");
        return null;
      }
      if (finishProcessing) finishProcessing(error.message || "Request failed.");
      try {
        await refresh();
      } catch {
        // Preserve the original mutation error when reconciliation is unavailable.
      }
      throw error;
    }
  }

  async function callApi(path, payload = null) {
    try {
      return await api(path, payload);
    } catch (error) {
      forceHideProcessingBar();
      setStatus(error.message);
      emitBackbone(backbone, "api.error", { path, error: error.message });
      activity("api.error", { path, error: error.message });
      return null;
    }
  }

  function practiScoreResponseErrorMessage(data, fallback) {
    if (typeof data?.error === "string") return data.error;
    if (data?.error && typeof data.error === "object") {
      return String(data.error.message || data.error.code || fallback);
    }
    return String(fallback || "Unexpected PractiScore response.");
  }

  async function openPractiScoreDashboard() {
    emitBackbone(backbone, "api.request", { path: "/api/practiscore/dashboard/open", payload: {} });
    activity("api.request", { path: "/api/practiscore/dashboard/open", payload: {} });
    const processing = processingForPath("/api/practiscore/dashboard/open", {});
    const finishProcessing = processing === null
      ? null
      : beginProcessing(processing.message, processing.detail, "/api/practiscore/dashboard/open");
    try {
      const response = await fetch("/api/practiscore/dashboard/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const result = await parseJsonResponse(response, "/api/practiscore/dashboard/open");
      if (!response.ok || result.error) throw new Error(result.error || response.statusText);
      if (finishProcessing) finishProcessing(result.status || "Ready.");
      setStatus(result.status || "Opened PractiScore dashboard in your browser.");
      emitBackbone(backbone, "api.response", { path: "/api/practiscore/dashboard/open", status: result.status || "Ready." });
      activity("api.response", { path: "/api/practiscore/dashboard/open", status: result.status || "Ready." });
      return result;
    } catch (error) {
      if (finishProcessing) finishProcessing(error.message || "PractiScore request failed.");
      forceHideProcessingBar();
      setStatus(error.message);
      emitBackbone(backbone, "api.error", { path: "/api/practiscore/dashboard/open", error: error.message });
      activity("api.error", { path: "/api/practiscore/dashboard/open", error: error.message });
      return null;
    }
  }

  async function refresh() {
    activity("api.refresh", {});
    emitBackbone(backbone, "api.refresh", {});
    const refreshRequestSequence = apiRequestSequence;
    try {
      const response = await fetch("/api/state");
      const data = await parseJsonResponse(response, "/api/state");
      if (!response.ok || data.error) throw new Error(data.error || response.statusText);
      if (refreshRequestSequence !== apiRequestSequence) return;
      applyRemoteState(data);
      requestRender();
    } catch (error) {
      setStatus(error.message);
      emitBackbone(backbone, "api.error", { path: "/api/state", error: error.message });
      activity("api.error", { path: "/api/state", error: error.message });
    }
  }

  function applyRemoteState(nextState, { preserveActiveInteraction = false } = {}) {
    if (!hasCompleteProjectState(nextState)) {
      throw new Error("Received invalid project state from the local server.");
    }
    const previousSelectionContext = runtime.pendingSelectionFallback
      || shotSelectionContext(runtime.selectedShotId, runtime.state)
      || shotSelectionContext(runtime.state?.project?.ui_state?.selected_shot_id, runtime.state);
    runtime.pendingSelectionFallback = null;
    const nextProjectId = nextState?.project?.id || "";
    const isSameProject = runtime.currentProjectId && nextProjectId && runtime.currentProjectId === nextProjectId;
    const shouldPreserveBootstrapProjectUiState = !runtime.initialProjectUiStateApplied && runtime.pendingBootstrapProjectUiStateOverride;
    if (runtime.currentProjectId && nextProjectId && runtime.currentProjectId !== nextProjectId) {
      resetLocalProjectView();
    }
    const remoteSelectedShotId = nextState.project.ui_state.selected_shot_id;
    let nextUiState = isSameProject || shouldPreserveBootstrapProjectUiState
      ? mergeProjectUiState(nextState.project.ui_state, readProjectUiStatePayload())
      : normalizeProjectUiState(nextState.project.ui_state);
    nextUiState.selected_shot_id = resolveSelectedShotId(
      nextState,
      nextUiState.selected_shot_id,
      previousSelectionContext,
      remoteSelectedShotId,
    );
    nextState.project.ui_state = nextUiState;
    if (isSameProject) {
      mergeProjectDetailsDraft(nextState.project);
      mergeMergeDraft(nextState.project);
      mergeOverlayPositionDraft(nextState.project);
      mergeOverlayStyleDraft(nextState.project);
      mergeOverlayTextBoxesDraft(nextState.project);
      mergePopupDraft(nextState.project);
      mergeExportDraft(nextState.project);
    }
    runtime.currentProjectId = nextProjectId;
    setStateValue(nextState);
    if (!preserveActiveInteraction) applyProjectUiState(nextUiState);
    runtime.initialProjectUiStateApplied = true;
    runtime.pendingBootstrapProjectUiStateOverride = false;
    if (!stateHasShot(runtime.state, runtime.selectedShotId)) {
      runtime.selectedShotId = stateHasShot(runtime.state, nextUiState.selected_shot_id) ? nextUiState.selected_shot_id : null;
    }
    syncSelectedShotId(runtime.state, previousSelectionContext);
    syncLocalProjectUiState();
    syncApiBackbone();
    emitBackbone(backbone, "api.remote_state.applied", { project_id: nextProjectId, same_project: Boolean(isSameProject) });
  }

  function defaultPractiScoreSessionPayload() {
    return {
      state: "not_authenticated",
      message: "Connect PractiScore to use your browser session for background sync.",
      details: {},
    };
  }

  function normalizePractiScoreSessionPayload(payload) {
    const normalized = defaultPractiScoreSessionPayload();
    if (!payload || typeof payload !== "object") return normalized;
    normalized.state = String(payload.state || normalized.state);
    normalized.message = String(payload.message || normalized.message);
    normalized.details = payload.details && typeof payload.details === "object" ? { ...payload.details } : {};
    return normalized;
  }

  function normalizePractiScoreRemoteMatches(matches) {
    if (!Array.isArray(matches)) return [];
    return matches
      .filter((item) => item && typeof item === "object" && String(item.remote_id || "").trim())
      .map((item) => ({
        remote_id: String(item.remote_id || "").trim(),
        label: String(item.label || "").trim(),
        match_type: String(item.match_type || "").trim(),
        event_name: String(item.event_name || "").trim(),
        event_date: String(item.event_date || "").trim(),
      }));
  }

  function defaultPractiScoreSyncPayload() {
    return {
      state: "idle",
      message: "No remote PractiScore sync activity yet.",
      matches: [],
      selected_remote_id: null,
      error_category: "",
      details: {},
    };
  }

  function normalizePractiScoreSyncPayload(payload) {
    const normalized = defaultPractiScoreSyncPayload();
    if (!payload || typeof payload !== "object") return normalized;
    normalized.state = String(payload.state || normalized.state);
    normalized.message = String(payload.message || normalized.message);
    normalized.matches = normalizePractiScoreRemoteMatches(payload.matches);
    normalized.selected_remote_id = payload.selected_remote_id === null || payload.selected_remote_id === undefined || String(payload.selected_remote_id).trim() === ""
      ? null
      : String(payload.selected_remote_id).trim();
    normalized.error_category = String(payload.error_category || "").trim();
    normalized.details = payload.details && typeof payload.details === "object" ? { ...payload.details } : {};
    return normalized;
  }

  function practiScoreSessionPayload() {
    return normalizePractiScoreSessionPayload(runtime.state?.practiscore_session);
  }

  function practiScoreSyncPayload() {
    return normalizePractiScoreSyncPayload(runtime.state?.practiscore_sync);
  }

  function applyPractiScoreSessionPayload(payload, { resetSync = false } = {}) {
    if (!runtime.state) return;
    runtime.state.practiscore_session = normalizePractiScoreSessionPayload(payload);
    if (resetSync) runtime.state.practiscore_sync = defaultPractiScoreSyncPayload();
  }

  function applyPractiScoreRoutePayload(payload) {
    if (!runtime.state || !payload || typeof payload !== "object") return;
    if (Object.prototype.hasOwnProperty.call(payload, "practiscore_session")) {
      runtime.state.practiscore_session = normalizePractiScoreSessionPayload(payload.practiscore_session);
    }
    if (Object.prototype.hasOwnProperty.call(payload, "practiscore_sync")) {
      runtime.state.practiscore_sync = normalizePractiScoreSyncPayload(payload.practiscore_sync);
    } else if (Array.isArray(payload.matches)) {
      runtime.state.practiscore_sync = normalizePractiScoreSyncPayload({
        ...practiScoreSyncPayload(),
        matches: payload.matches,
      });
    }
    if (Object.prototype.hasOwnProperty.call(payload, "practiscore_options") && payload.practiscore_options && typeof payload.practiscore_options === "object") {
      runtime.state.practiscore_options = {
        ...(runtime.state.practiscore_options || {}),
        ...payload.practiscore_options,
      };
    }
  }

  syncApiBackbone();

  return Object.freeze({
    hasCompleteProjectState,
    stateHasShot,
    api,
    callApi,
    practiScoreResponseErrorMessage,
    openPractiScoreDashboard,
    refresh,
    applyRemoteState,
    defaultPractiScoreSessionPayload,
    normalizePractiScoreSessionPayload,
    normalizePractiScoreRemoteMatches,
    defaultPractiScoreSyncPayload,
    normalizePractiScoreSyncPayload,
    practiScoreSessionPayload,
    practiScoreSyncPayload,
    applyPractiScoreSessionPayload,
    applyPractiScoreRoutePayload,
  });
}
