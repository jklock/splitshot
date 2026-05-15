export function createProjectPane({
  $ = (id) => document.getElementById(id),
  windowObject = window,
  documentObject = document,
  getState = () => null,
  getProjectDetailsDraft = () => ({ name: null, description: null }),
  setProjectDetailsDraft = () => {},
  getProjectFolderProbeRequestId = () => 0,
  setProjectFolderProbeRequestId = () => {},
  controlIsActive = (control) => Boolean(control) && documentObject.activeElement === control,
  normalizeToolId = (tool) => String(tool || "project"),
  setActiveTool = () => {},
  applyProjectUiStatePayload = async () => null,
  cancelPendingExportDrafts = () => {},
  flushPendingSettingsDefaults = async () => {},
  cancelAutoApplySettingsDefaults = () => {},
  shouldSyncShotMLSettingsBeforePrimaryImport = () => true,
  hasPendingPrimaryImportKeepaliveDrafts = () => true,
  readShotMLSettingsPayload = () => ({}),
  readOverlayPayload = () => ({}),
  readMergePayload = () => ({}),
  flushPendingMergeSourceCommits = async () => {},
  readExportLayoutPayload = () => ({}),
  readExportSettingsPayload = () => ({}),
  readScoringPayload = () => ({}),
  callApi = async () => null,
  sendKeepaliveJson = () => false,
  sendProjectUiStateKeepalive = () => false,
  pickPath = async () => "",
  fileName = (value) => String(value || ""),
  splitSeconds = (value) => String(value ?? ""),
  formatNumber = (value) => String(value ?? ""),
  formatPractiScoreTime = (value) => String(value ?? ""),
  autoApplyProjectDetails = () => {},
  autoApplyPractiScoreContext = () => {},
  renderDetailsList = () => {},
  renderHeader = () => {},
  setStatus = () => {},
  activity = () => {},
  fetchImpl = (...args) => fetch(...args),
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function currentProjectDetailsDraft() {
    const draft = getProjectDetailsDraft();
    return draft && typeof draft === "object"
      ? draft
      : { name: null, description: null };
  }

  function setProjectDetailsDraftPatch(patch = {}) {
    const nextDraft = {
      name: null,
      description: null,
      ...currentProjectDetailsDraft(),
      ...patch,
    };
    setProjectDetailsDraft(nextDraft);
    return nextDraft;
  }

  function normalizeProjectNameValue(value) {
    return String(value ?? "").trim() || "Untitled Project";
  }

  function projectDetailValue(field, project = currentState()?.project) {
    const savedValue = field === "name"
      ? normalizeProjectNameValue(project?.name)
      : String(project?.description || "");
    const draftValue = currentProjectDetailsDraft()[field];
    return draftValue === null ? savedValue : draftValue;
  }

  function applyProjectDetailsDraft(payload = {}) {
    const project = currentState()?.project;
    const nextDraft = { ...currentProjectDetailsDraft() };
    if (Object.prototype.hasOwnProperty.call(payload, "name")) {
      const nextNameDraft = String(payload.name ?? "");
      const savedName = normalizeProjectNameValue(project?.name);
      nextDraft.name = normalizeProjectNameValue(nextNameDraft) === savedName ? null : nextNameDraft;
      if (project) project.name = normalizeProjectNameValue(nextNameDraft);
    }
    if (Object.prototype.hasOwnProperty.call(payload, "description")) {
      const nextDescriptionDraft = String(payload.description ?? "");
      const savedDescription = String(project?.description || "");
      nextDraft.description = nextDescriptionDraft === savedDescription ? null : nextDescriptionDraft;
      if (project) project.description = nextDescriptionDraft;
    }
    setProjectDetailsDraftPatch(nextDraft);
  }

  function mergeProjectDetailsDraft(project) {
    if (!project) return;
    const nextDraft = { ...currentProjectDetailsDraft() };
    if (nextDraft.name !== null) {
      const draftName = String(nextDraft.name);
      if (normalizeProjectNameValue(draftName) === normalizeProjectNameValue(project.name)) {
        nextDraft.name = null;
      } else {
        project.name = normalizeProjectNameValue(draftName);
      }
    }
    if (nextDraft.description !== null) {
      const draftDescription = String(nextDraft.description);
      if (draftDescription === String(project.description || "")) {
        nextDraft.description = null;
      } else {
        project.description = draftDescription;
      }
    }
    setProjectDetailsDraftPatch(nextDraft);
  }

  function normalizedPractiScorePlaceValue(rawValue) {
    if (rawValue === null || rawValue === undefined || String(rawValue).trim() === "") return null;
    const numeric = Number(rawValue);
    if (!Number.isFinite(numeric) || numeric < 1) return null;
    return Math.trunc(numeric);
  }

  function practiScoreCompetitors() {
    return Array.isArray(currentState()?.practiscore_options?.competitors)
      ? currentState().practiscore_options.competitors
      : [];
  }

  function practiScoreStageValues() {
    return [...new Set(
      (Array.isArray(currentState()?.practiscore_options?.stage_numbers) ? currentState().practiscore_options.stage_numbers : [])
        .map((value) => String(value || "").trim())
        .filter(Boolean),
    )];
  }

  function practiScoreNameValues() {
    return [...new Set(practiScoreCompetitors().map((option) => String(option.name || "").trim()).filter(Boolean))];
  }

  function practiScorePlaceValues() {
    return [...new Set(
      practiScoreCompetitors()
        .map((option) => normalizedPractiScorePlaceValue(option.place))
        .filter((value) => value !== null),
    )].map((value) => String(value));
  }

  function practiScoreSelectionValue(value) {
    if (value === null || value === undefined) return "";
    return String(value).trim();
  }

  function preferredPractiScoreSelection(explicitValue, controlId, fallbackValue) {
    if (explicitValue !== undefined) return practiScoreSelectionValue(explicitValue);
    const controlValue = practiScoreSelectionValue($(controlId)?.value);
    if (controlValue) return controlValue;
    return practiScoreSelectionValue(fallbackValue);
  }

  function renderPractiScoreSelect(selectId, values, emptyLabel, selectedValue = "") {
    const select = $(selectId);
    if (!(select instanceof HTMLSelectElement)) return;
    const optionValues = [...new Set((values || []).map((value) => practiScoreSelectionValue(value)).filter(Boolean))];
    const desiredValue = practiScoreSelectionValue(selectedValue);
    const activeValue = controlIsActive(select) ? practiScoreSelectionValue(select.value) : "";
    const preservedValue = activeValue || desiredValue;
    if (preservedValue && !optionValues.includes(preservedValue)) optionValues.unshift(preservedValue);
    select.innerHTML = "";
    const emptyOption = documentObject.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = emptyLabel;
    select.appendChild(emptyOption);
    optionValues.forEach((value) => {
      const option = documentObject.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    select.value = preservedValue && optionValues.includes(preservedValue) ? preservedValue : "";
  }

  function renderPractiScoreOptionLists(selectedValues = {}) {
    renderPractiScoreSelect(
      "match-stage-number",
      practiScoreStageValues(),
      "Select stage",
      preferredPractiScoreSelection(selectedValues.stage_number, "match-stage-number", currentState()?.project?.scoring?.stage_number),
    );
    renderPractiScoreSelect(
      "match-competitor-name",
      practiScoreNameValues(),
      "Select competitor",
      preferredPractiScoreSelection(selectedValues.competitor_name, "match-competitor-name", currentState()?.project?.scoring?.competitor_name),
    );
    renderPractiScoreSelect(
      "match-competitor-place",
      practiScorePlaceValues(),
      "Select place",
      preferredPractiScoreSelection(selectedValues.competitor_place, "match-competitor-place", currentState()?.project?.scoring?.competitor_place),
    );
  }

  function syncPractiScoreSelectionFields(changedField) {
    const competitors = practiScoreCompetitors();
    const stageSelect = $("match-stage-number");
    const nameSelect = $("match-competitor-name");
    const placeSelect = $("match-competitor-place");
    if (!(nameSelect instanceof HTMLSelectElement) || !(placeSelect instanceof HTMLSelectElement)) {
      renderPractiScoreOptionLists();
      return;
    }

    if (competitors.length === 0) {
      renderPractiScoreOptionLists({
        stage_number: practiScoreSelectionValue(stageSelect?.value),
        competitor_name: nameSelect.value,
        competitor_place: placeSelect.value,
      });
      return;
    }

    const selectedName = nameSelect.value.trim();
    const selectedPlace = normalizedPractiScorePlaceValue(placeSelect.value);
    if (changedField === "name") {
      const matches = competitors.filter((option) => option.name === selectedName);
      if (!selectedName || matches.length === 0) {
        placeSelect.value = "";
      } else if (matches.length === 1 && matches[0].place !== null) {
        placeSelect.value = String(matches[0].place);
      } else if (selectedPlace !== null && !matches.some((option) => Number(option.place) === selectedPlace)) {
        placeSelect.value = "";
      }
    }
    if (changedField === "place") {
      if (selectedPlace === null) {
        nameSelect.value = "";
      } else {
        const matches = competitors.filter((option) => Number(option.place) === selectedPlace);
        if (matches.length === 0) {
          nameSelect.value = "";
        } else if (matches.length === 1) {
          nameSelect.value = matches[0].name;
        } else if (selectedName && !matches.some((option) => option.name === selectedName)) {
          nameSelect.value = "";
        }
      }
    }

    renderPractiScoreOptionLists({
      stage_number: practiScoreSelectionValue(stageSelect?.value),
      competitor_name: nameSelect.value,
      competitor_place: placeSelect.value,
    });
  }

  function readProjectDetailsPayload() {
    return {
      name: $("project-name")?.value ?? projectDetailValue("name"),
      description: $("project-description")?.value ?? projectDetailValue("description"),
    };
  }

  function readPractiScoreContextPayload() {
    return {
      match_type: $("match-type")?.value || "",
      stage_number: $("match-stage-number")?.value ? Number($("match-stage-number").value) : "",
      competitor_name: $("match-competitor-name")?.value.trim() || "",
      competitor_place: normalizedPractiScorePlaceValue($("match-competitor-place")?.value) ?? "",
    };
  }

  function validatePractiScoreSelection() {
    return readPractiScoreContextPayload();
  }

  function queueNonBlockingProjectDraftFlush() {
    sendKeepaliveJson("/api/project/details", readProjectDetailsPayload());
    sendKeepaliveJson("/api/project/practiscore", readPractiScoreContextPayload());
    sendProjectUiStateKeepalive();
    sendKeepaliveJson("/api/overlay", readOverlayPayload());
    sendKeepaliveJson("/api/merge", readMergePayload());
    flushPendingMergeSourceCommits({ keepalive: true });
    sendKeepaliveJson("/api/export/settings", readExportLayoutPayload());
    sendKeepaliveJson("/api/export/settings", readExportSettingsPayload());
    sendKeepaliveJson("/api/scoring/profile", { ruleset: $("scoring-preset")?.value || "" });
    sendKeepaliveJson("/api/scoring", readScoringPayload());
  }

  async function flushPendingProjectDrafts(options = {}) {
    if (!currentState()?.project) return;
    const primaryImport = Boolean(options?.primaryImport);
    cancelPendingExportDrafts();
    await flushPendingSettingsDefaults();
    if (!primaryImport || shouldSyncShotMLSettingsBeforePrimaryImport()) {
      await callApi("/api/analysis/shotml-settings", { settings: readShotMLSettingsPayload(), rerun: false });
    }
    if (primaryImport) {
      if (hasPendingPrimaryImportKeepaliveDrafts()) {
        queueNonBlockingProjectDraftFlush();
      }
      return;
    }
    await callApi("/api/project/details", readProjectDetailsPayload());
    await callApi("/api/project/practiscore", readPractiScoreContextPayload());
    await applyProjectUiStatePayload();
    await callApi("/api/overlay", readOverlayPayload());
    await callApi("/api/merge", readMergePayload());
    await flushPendingMergeSourceCommits();
    await callApi("/api/export/settings", readExportLayoutPayload());
    await callApi("/api/export/settings", readExportSettingsPayload());
    await callApi("/api/scoring/profile", { ruleset: $("scoring-preset")?.value || "" });
    await callApi("/api/scoring", readScoringPayload());
  }

  function flushPendingProjectDraftsKeepalive() {
    if (!currentState()?.project) return;
    cancelPendingExportDrafts();
    sendKeepaliveJson("/api/analysis/shotml-settings", { settings: readShotMLSettingsPayload(), rerun: false });
    queueNonBlockingProjectDraftFlush();
  }

  async function importTypedPath(targetId, apiPath, label) {
    const path = $(targetId)?.value.trim() || "";
    if (!path) {
      setStatus(`${label} video path is required.`);
      return null;
    }
    if (apiPath === "/api/import/primary") {
      await flushPendingProjectDrafts({ primaryImport: true });
    }
    return callApi(apiPath, { path });
  }

  function normalizeProjectFolderInput(path) {
    return String(path || "").trim();
  }

  function formatShotMlConfidenceSummary(shots = []) {
    const values = shots
      .map((shot) => Number(shot?.shotml_confidence ?? shot?.confidence))
      .filter((value) => Number.isFinite(value));
    if (values.length === 0) return "--";
    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    return `${formatNumber(average * 100, 1)}%`;
  }

  function renderOwnedSummaryList(id, rows = [], className = "") {
    const list = $(id);
    if (!(list instanceof HTMLElement)) return;
    list.className = ["details", "pane-summary-list", className].filter(Boolean).join(" ");
    list.replaceChildren();
    rows.forEach(([label, value]) => {
      const term = documentObject.createElement("dt");
      term.textContent = label;
      const description = documentObject.createElement("dd");
      description.textContent = value;
      list.append(term, description);
    });
  }

  function ssStageTimeSeconds(state) {
    const beepMs = Number(state?.project?.analysis?.beep_time_ms_primary);
    const shots = Array.isArray(state?.project?.analysis?.shots) ? state.project.analysis.shots : [];
    if (!Number.isFinite(beepMs) || shots.length === 0) return null;
    let finalShotMs = null;
    shots.forEach((shot) => {
      const shotTimeMs = Number(shot?.time_ms);
      if (!Number.isFinite(shotTimeMs)) return;
      if (finalShotMs === null || shotTimeMs > finalShotMs) finalShotMs = shotTimeMs;
    });
    if (finalShotMs === null) return null;
    return Math.max(0, (finalShotMs - beepMs) / 1000);
  }

  function renderPractiScoreImportSummary() {
    const state = currentState();
    const imported = state.scoring_summary?.imported_stage;
    const stagedSource = state.practiscore_options?.source_name || "";
    const stagedMatchType = state.practiscore_options?.detected_match_type || "";
    const stagedStages = Array.isArray(state.practiscore_options?.stage_numbers)
      ? state.practiscore_options.stage_numbers
      : [];
    const stagedCompetitorCount = practiScoreCompetitors().length;
    const status = $("practiscore-status");
    if (!imported) {
      if (status) status.textContent = stagedSource ? `${stagedSource} loaded` : "No results imported";
      renderOwnedSummaryList("practiscore-import-summary", stagedSource ? [
        ["Stage Start (Beep)", "--"],
        ["Shots in Stage", stagedCompetitorCount > 0 ? "0" : "0"],
        ["SS Stage Time", "--"],
        ["PS Stage Time", "--"],
        ["Video Length", "--"],
        ["ShotML Confidence", "--"],
      ] : [], "project-practiscore-summary");
      return;
    }
    const beepMs = state.project?.analysis?.beep_time_ms_primary;
    const shots = Array.isArray(state.project?.analysis?.shots) ? state.project.analysis.shots : [];
    const ssStageSeconds = ssStageTimeSeconds(state);
    const psStageSeconds = imported.raw_seconds ?? state.scoring_summary?.official_raw_seconds;
    const videoDurationMs = state.project?.primary_video?.duration_ms;
    if (status) status.textContent = `${stagedMatchType ? stagedMatchType.toUpperCase() : "PractiScore"} Stage ${imported.stage_number} imported`;
    renderOwnedSummaryList("practiscore-import-summary", [
      ["Stage Start (Beep)", splitSeconds(beepMs)],
      ["Shots in Stage", shots.length > 0 ? String(shots.length) : "0"],
      ["SS Stage Time", formatPractiScoreTime(ssStageSeconds)],
      ["PS Stage Time", formatPractiScoreTime(psStageSeconds)],
      ["Video Length", splitSeconds(videoDurationMs)],
      ["ShotML Confidence", formatShotMlConfidenceSummary(shots)],
    ], "project-practiscore-summary");
  }

  function hasActiveProject() {
    return Boolean(String(currentState()?.project?.path || "").trim());
  }

  function gatedProjectActionMessage() {
    return "Please create / select project.";
  }

  function setProjectActionAvailability() {
    const enabled = hasActiveProject();
    ["open-practiscore-dashboard", "import-practiscore", "browse-primary-path", "primary-file-path"].forEach((id) => {
      const control = $(id);
      if (control && "disabled" in control) control.disabled = !enabled;
    });
  }

  function createdProjectFoldersMessage(folderName, missingDirs) {
    if (!Array.isArray(missingDirs) || missingDirs.length === 0) return "";
    const suffix = missingDirs.length === 1 ? "folder" : "folders";
    return `Project folder ${folderName} was missing ${missingDirs.join(", ")}. SplitShot created the missing ${suffix}.`;
  }

  function comparableProjectFolderPath(path) {
    let normalized = normalizeProjectFolderInput(path).replace(/[\\/]+$/, "");
    normalized = normalized.replace(/[\\/]project\.json$/i, "");
    return normalized;
  }

  function sameProjectFolderPath(left, right) {
    return comparableProjectFolderPath(left) === comparableProjectFolderPath(right);
  }

  async function probeProjectFolder(path) {
    const targetPath = normalizeProjectFolderInput(path);
    const requestId = getProjectFolderProbeRequestId() + 1;
    setProjectFolderProbeRequestId(requestId);
    const response = await fetchImpl("/api/project/probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: targetPath }),
    });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    if (requestId !== getProjectFolderProbeRequestId()) {
      throw new Error("Project folder selection changed. Try again.");
    }
    if (!sameProjectFolderPath(data.path || targetPath, targetPath)) {
      throw new Error("Project folder probe returned a different path.");
    }
    return {
      path: targetPath,
      normalized_path: comparableProjectFolderPath(data.normalized_path || data.path || targetPath),
      has_project_file: Boolean(data.has_project_file),
      missing_required_dirs: Array.isArray(data.missing_required_dirs) ? data.missing_required_dirs.map((value) => String(value)) : [],
      request_id: requestId,
    };
  }

  async function browseProjectPath() {
    return pickPath("project_folder", "project-path", async (selectedPath) => {
      await useProjectFolder(selectedPath);
    });
  }

  async function applyConfiguredProjectLandingTool(options = {}) {
    const forceProjectTool = Boolean(options?.forceProjectTool);
    const reopenLastTool = Boolean(currentState()?.settings?.reopen_last_tool ?? true);
    const configuredTool = forceProjectTool
      ? "project"
      : reopenLastTool
        ? normalizeToolId(currentState()?.settings?.default_tool || currentState()?.project?.ui_state?.active_tool || "project")
        : "project";
    setActiveTool(configuredTool, { collapseExpandedLayout: forceProjectTool, persistUiState: false });
    return applyProjectUiStatePayload();
  }

  async function createNewProject(path = "") {
    const targetPath = normalizeProjectFolderInput(path);
    if (!targetPath) {
      return pickPath("project_folder", "project-path", async (selectedPath) => {
        await createNewProject(selectedPath);
      });
    }

    try {
      const probeResult = await probeProjectFolder(targetPath);
      const projectPath = probeResult.normalized_path || targetPath;
      if (probeResult.has_project_file) {
        const shouldReplace = windowObject.confirm(`A SplitShot project already exists in:\n${targetPath}\n\nReplace it with a new blank project?`);
        if (!shouldReplace) {
          setStatus("New project creation cancelled.");
          return null;
        }
      }
      if (probeResult.request_id !== getProjectFolderProbeRequestId()) {
        setStatus("Project folder selection changed. Try again.");
        return null;
      }

      await flushPendingSettingsDefaults();
      cancelAutoApplySettingsDefaults();
      const resetResult = await callApi("/api/project/new", {});
      if (!resetResult) return null;
      await flushPendingProjectDrafts();
      const savedResult = await callApi("/api/project/save", { path: projectPath });
      if (savedResult) {
        await applyConfiguredProjectLandingTool({ forceProjectTool: true });
        const folderMessage = createdProjectFoldersMessage(fileName(projectPath), probeResult.missing_required_dirs);
        if (folderMessage) {
          windowObject.alert(folderMessage);
          setStatus(folderMessage);
        }
      }
      return savedResult;
    } catch (error) {
      setStatus(error.message);
      activity("api.error", { path: "/api/project/new", error: error.message });
      return null;
    }
  }

  async function useProjectFolder(path = "") {
    const targetPath = normalizeProjectFolderInput(path);
    if (!targetPath) {
      return pickPath("project_folder", "project-path", async (selectedPath) => {
        await useProjectFolder(selectedPath);
      });
    }

    await flushPendingProjectDrafts();
    const currentPath = normalizeProjectFolderInput(currentState()?.project?.path || "");
    if (currentPath && sameProjectFolderPath(currentPath, targetPath)) {
      const result = await callApi("/api/project/save", { path: targetPath });
      if (result) await applyConfiguredProjectLandingTool({ forceProjectTool: true });
      return result;
    }

    try {
      const probeResult = await probeProjectFolder(targetPath);
      const projectPath = probeResult.normalized_path || targetPath;
      if (!probeResult.has_project_file) {
        const shouldCreate = windowObject.confirm(`No project.json found in:\n${targetPath}\n\nCreate this folder for the current project?`);
        if (!shouldCreate) {
          setStatus("Project folder selection cancelled.");
          return null;
        }
        if (probeResult.request_id !== getProjectFolderProbeRequestId()) {
          setStatus("Project folder selection changed. Try again.");
          return null;
        }
        const resetResult = await callApi("/api/project/new", {});
        if (!resetResult) return null;
        const result = await callApi("/api/project/save", { path: projectPath });
        if (result) {
          await applyConfiguredProjectLandingTool({ forceProjectTool: true });
          const folderMessage = createdProjectFoldersMessage(fileName(projectPath), probeResult.missing_required_dirs);
          if (folderMessage) {
            windowObject.alert(folderMessage);
            setStatus(folderMessage);
          }
        }
        return result;
      }

      if (probeResult.request_id !== getProjectFolderProbeRequestId()) {
        setStatus("Project folder selection changed. Try again.");
        return null;
      }
      const result = await callApi("/api/project/open", { path: projectPath });
      if (result) await applyConfiguredProjectLandingTool({ forceProjectTool: true });
      return result;
    } catch (error) {
      setStatus(error.message);
      activity("api.error", { path: "/api/project/probe", error: error.message });
      return null;
    }
  }

  function scheduleProjectDetailsApply() {
    const payload = readProjectDetailsPayload();
    applyProjectDetailsDraft(payload);
    renderHeader();
    autoApplyProjectDetails(payload);
  }

  function schedulePractiScoreContextApply() {
    autoApplyPractiScoreContext(readPractiScoreContextPayload());
  }

  return Object.freeze({
    normalizeProjectNameValue,
    projectDetailValue,
    applyProjectDetailsDraft,
    mergeProjectDetailsDraft,
    normalizedPractiScorePlaceValue,
    practiScoreCompetitors,
    practiScoreStageValues,
    practiScoreNameValues,
    practiScorePlaceValues,
    practiScoreSelectionValue,
    preferredPractiScoreSelection,
    renderPractiScoreSelect,
    renderPractiScoreOptionLists,
    syncPractiScoreSelectionFields,
    readProjectDetailsPayload,
    readPractiScoreContextPayload,
    validatePractiScoreSelection,
    flushPendingProjectDrafts,
    flushPendingProjectDraftsKeepalive,
    importTypedPath,
    renderPractiScoreImportSummary,
    normalizeProjectFolderInput,
    hasActiveProject,
    gatedProjectActionMessage,
    setProjectActionAvailability,
    createdProjectFoldersMessage,
    comparableProjectFolderPath,
    sameProjectFolderPath,
    probeProjectFolder,
    browseProjectPath,
    createNewProject,
    applyConfiguredProjectLandingTool,
    useProjectFolder,
    scheduleProjectDetailsApply,
    schedulePractiScoreContextApply,
  });
}
