export function createProjectPane({
  $ = (id) => document.getElementById(id),
  windowObject = window,
  documentObject = document,
  getState = () => null,
  getProjectDetailsDraft = () => ({ name: null, description: null, output_root: null }),
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
  formatMatchType = (matchType) => ({
    uspsa: "USPSA",
    ipsc: "IPSC",
    idpa: "IDPA",
    steel_challenge: "Steel Challenge",
  }[String(matchType || "").toLowerCase()] || "PractiScore"),
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
      : { name: null, description: null, output_root: null };
  }

  function setProjectDetailsDraftPatch(patch = {}) {
    const nextDraft = {
      name: null,
      description: null,
      output_root: null,
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
    if (Object.prototype.hasOwnProperty.call(payload, "output_root")) {
      const nextOutputRootDraft = String(payload.output_root ?? "");
      const savedOutputRoot = String(project?.output_root || "");
      nextDraft.output_root = nextOutputRootDraft === savedOutputRoot ? null : nextOutputRootDraft;
      if (project) project.output_root = nextOutputRootDraft;
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
    if (nextDraft.output_root !== null) {
      const draftOutputRoot = String(nextDraft.output_root);
      if (draftOutputRoot === String(project.output_root || "")) {
        nextDraft.output_root = null;
      } else {
        project.output_root = draftOutputRoot;
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

  function ensurePractiScoreSelectionControls() {
    const options = currentState()?.practiscore_options;
    if (!options?.competitors?.length) return;
    const competitorSelect = $("match-competitor-name");
    const classSelect = $("match-class");
    const divisionSelect = $("match-division");
    if (!competitorSelect && !classSelect && !divisionSelect) return;

    const competitors = practiScoreCompetitors();
    const competitorNames = [...new Set(competitors.map((c) => String(c.name || "").trim()).filter(Boolean))];
    const classValues = [...new Set(competitors.map((c) => String(c.classification || "").trim()).filter(Boolean))];
    const divisionValues = [...new Set(competitors.map((c) => String(c.division || "").trim()).filter(Boolean))];

    if (competitorSelect && competitorSelect.options.length <= 1) {
      renderPractiScoreSelect("match-competitor-name", competitorNames, "Select competitor", currentState()?.project?.scoring?.competitor_name || "");
    }
    if (classSelect && classSelect.options.length <= 1) {
      renderPractiScoreSelect("match-class", classValues, "Class", currentState()?.project?.scoring?.classification || "");
    }
    if (divisionSelect && divisionSelect.options.length <= 1) {
      renderPractiScoreSelect("match-division", divisionValues, "Division", currentState()?.project?.scoring?.division || "");
    }
  }

  function renderPractiScoreSelect(selectId, values, emptyLabel, selectedValue = "") {
    const select = $(selectId);
    if (!(select instanceof HTMLSelectElement)) return { selectId, values, emptyLabel, selectedValue };
    const currentValue = select.value || selectedValue;
    select.replaceChildren();
    const emptyOption = documentObject.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = emptyLabel;
    select.appendChild(emptyOption);
    values.forEach((value) => {
      const option = documentObject.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    const hasSelected = Array.from(select.options).some((option) => option.value === currentValue);
    if (hasSelected) select.value = currentValue;
    return { selectId, values, emptyLabel, selectedValue: select.value };
  }

  function renderPractiScoreOptionLists(selectedValues = {}) {
    const options = currentState()?.practiscore_options;
    if (!options?.competitors?.length) {
      ["match-competitor-name", "match-competitor-place", "match-class", "match-division"].forEach((id) => {
        const select = $(id);
        if (select instanceof HTMLSelectElement) {
          select.replaceChildren();
          const emptyOption = documentObject.createElement("option");
          emptyOption.value = "";
          emptyOption.textContent = id === "match-competitor-name" ? "No competitor data" : "--";
          select.appendChild(emptyOption);
        }
      });
      return selectedValues;
    }

    const competitors = practiScoreCompetitors();
    const competitorNames = [...new Set(competitors.map((c) => String(c.name || "").trim()).filter(Boolean))];
    const placeValues = [...new Set(competitors.map((c) => normalizedPractiScorePlaceValue(c.place)).filter((v) => v !== null))].sort((a, b) => a - b).map(String);
    const classValues = [...new Set(competitors.map((c) => String(c.classification || "").trim()).filter(Boolean))];
    const divisionValues = [...new Set(competitors.map((c) => String(c.division || "").trim()).filter(Boolean))];

    renderPractiScoreSelect("match-competitor-name", competitorNames, "Select competitor", selectedValues.competitor_name || currentState()?.project?.scoring?.competitor_name || "");
    renderPractiScoreSelect("match-competitor-place", placeValues, "Place", selectedValues.competitor_place || String(currentState()?.project?.scoring?.competitor_place || ""));
    renderPractiScoreSelect("match-class", classValues, "Class", selectedValues.classification || currentState()?.project?.scoring?.classification || "");
    renderPractiScoreSelect("match-division", divisionValues, "Division", selectedValues.division || currentState()?.project?.scoring?.division || "");
    return { ...selectedValues, competitor_name: $("match-competitor-name")?.value || "", competitor_place: $("match-competitor-place")?.value || "", classification: $("match-class")?.value || "", division: $("match-division")?.value || "" };
  }

  function syncPractiScoreSelectionFields(changedField) {
    const competitors = practiScoreCompetitors();
    if (!competitors.length) return changedField;

    const nameSelect = $("match-competitor-name");
    const placeSelect = $("match-competitor-place");
    const classSelect = $("match-class");
    const divisionSelect = $("match-division");

    if (changedField === "match-competitor-name") {
      const selectedName = nameSelect?.value || "";
      const matchingCompetitors = competitors.filter((c) => String(c.name || "").trim() === selectedName);
      if (matchingCompetitors.length === 1) {
        const competitor = matchingCompetitors[0];
        if (competitor.place && placeSelect) placeSelect.value = String(competitor.place);
        if (competitor.classification && classSelect) {
          const classOpt = [...classSelect.options].find((o) => o.value === competitor.classification);
          if (classOpt) classSelect.value = competitor.classification;
        }
        if (competitor.division && divisionSelect) {
          const divOpt = [...divisionSelect.options].find((o) => o.value === competitor.division);
          if (divOpt) divisionSelect.value = competitor.division;
        }
      }
    } else if (changedField === "match-competitor-place") {
      const selectedPlace = normalizedPractiScorePlaceValue(placeSelect?.value);
      if (selectedPlace !== null) {
        const matchingCompetitors = competitors.filter((c) => c.place === selectedPlace);
        if (matchingCompetitors.length === 1 && nameSelect) {
          nameSelect.value = String(matchingCompetitors[0].name || "");
          if (matchingCompetitors[0].classification && classSelect) classSelect.value = matchingCompetitors[0].classification;
          if (matchingCompetitors[0].division && divisionSelect) divisionSelect.value = matchingCompetitors[0].division;
        }
      }
    }

    return changedField;
  }

  function readProjectDetailsPayload() {
    return {
      name: $("project-name")?.value ?? projectDetailValue("name"),
      description: $("project-description")?.value ?? projectDetailValue("description"),
      output_root: $("project-output-root")?.value ?? String(currentState()?.project?.output_root || ""),
    };
  }

  function readPractiScoreContextPayload() {
    const scoring = currentState()?.project?.scoring || {};
    return {
      match_type: $("match-type")?.value || String(scoring.match_type || ""),
      competitor_name: $("match-competitor-name")?.value || String(scoring.competitor_name || ""),
      competitor_place: $("match-competitor-place")?.value || String(scoring.competitor_place ?? ""),
      classification: $("match-class")?.value || String(scoring.classification || ""),
      division: $("match-division")?.value || String(scoring.division || ""),
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
    const scoring = state?.project?.scoring || {};
    const status = $("practiscore-status");
    if (stagedSource) {
      if (status) status.textContent = imported ? `${formatMatchType(stagedMatchType)} imported` : `${stagedSource} loaded`;
    } else if (status) {
      status.textContent = "No results imported";
    }
    const summary = $("practiscore-import-summary");
    if (summary) {
      summary.textContent = "";
      summary.hidden = true;
    }
  }

  function hasActiveProject() {
    return Boolean(String(currentState()?.project?.path || "").trim());
  }

  function gatedProjectActionMessage() {
    return "Please create / select project.";
  }

  function setProjectActionAvailability() {
    const enabled = hasActiveProject();
    ["open-practiscore-dashboard", "import-practiscore"].forEach((id) => {
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
    ensurePractiScoreSelectionControls,
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
