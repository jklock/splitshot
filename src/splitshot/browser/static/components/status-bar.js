export function createStatusBarComponent({
  $ = (id) => document.getElementById(id),
  getState = () => null,
  normalizeProjectNameValue = (value) => String(value || "").trim() || "Untitled Project",
  fileName = (path) => path,
  syncControlValue = () => {},
  setProjectActionAvailability = () => {},
  renderDetailsList = () => {},
  splitSeconds = (value) => String(value),
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function timingSummaryRows() {
    const state = currentState();
    return [
      ["Draw", splitSeconds(state.metrics.draw_ms)],
      ["Raw", splitSeconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms)],
      ["Shots", String(state.metrics.total_shots || 0)],
      ["Avg Split", splitSeconds(state.metrics.average_split_ms)],
      ["Beep", splitSeconds(state.metrics.beep_ms)],
    ];
  }

  function renderTimingSummary() {
    const state = currentState();
    const enabled = $("timing-enabled")?.checked ?? true;
    const totalShots = Number(state?.metrics?.total_shots || 0);
    const result = $("timing-result");
    const summary = $("timing-summary");
    if (result) result.textContent = enabled ? splitSeconds(state.metrics.stage_time_ms ?? state.metrics.raw_time_ms) : "--";
    if (summary) {
      summary.textContent = !enabled
        ? "Splits disabled."
        : totalShots > 0
        ? "Current split timing."
        : "No timing data.";
    }
    renderDetailsList("timing-imported-summary", enabled && totalShots > 0 ? timingSummaryRows() : []);
  }

  function renderHeader() {
    const state = currentState();
    const projectName = normalizeProjectNameValue(state?.project?.name);
    const projectPath = String(state?.project?.path || "").trim();
    const hasProject = Boolean(projectPath);
    const projectFolderLabel = hasProject ? fileName(projectPath.replace(/[\\/]+$/, "")) : "";
    $("project-title").textContent = projectName;
    $("rail-project").textContent = projectName;
    $("status").textContent = state.status;
    const primaryName = state?.media?.primary_available
      ? (state.media.primary_display_name || fileName(state?.project?.primary_video?.path))
      : "No Video Selected";
    $("current-file").textContent = primaryName;
    const statusCopy = $("status-copy");
    if (statusCopy) statusCopy.textContent = state.status;
    const mergeCount = (state?.project?.merge_sources || []).length;
    $("primary-file-path").placeholder = "Please select a video";
    syncControlValue($("primary-file-path"), state?.project?.primary_video?.path ? fileName(state.project.primary_video.path) : "");
    $("project-path").placeholder = "Please create / select project";
    syncControlValue($("project-path"), projectFolderLabel);
    $("media-badge").textContent = state?.media?.primary_available
      ? `Primary: ${primaryName}${mergeCount > 0 ? ` • ${mergeCount} added item${mergeCount === 1 ? "" : "s"}` : ""}`
      : "No Video Selected";
  }

  function renderStats() {
    setProjectActionAvailability();
    renderTimingSummary();
    $("apply-threshold").disabled = !currentState()?.project?.primary_video?.path;
  }

  return Object.freeze({
    renderHeader,
    renderStats,
    timingSummaryRows,
    renderTimingSummary,
  });
}
