export function createShellRuntime({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  getActiveTool = () => "project",
  setActiveTool = () => {},
  getRailCollapsed = () => false,
  setRailCollapsed = () => {},
  getOverlayVisibilityPosition = () => "bottom",
  setOverlayVisibilityPosition = () => {},
  getOverlayStyleMode = () => "square",
  setOverlayStyleMode = () => {},
  getOverlaySpacing = () => 8,
  setOverlaySpacing = () => {},
  getOverlayMargin = () => 8,
  setOverlayMargin = () => {},
  getExportPathDraft = () => "",
  setExportPathDraft = () => {},
  resetMergeDraft = () => {},
  resetExportDraft = () => {},
  getOverlayFrame = () => null,
  getPopupFilterMode = () => "all",
  getPopupAuthoringCollapsed = () => false,
  setPopupAuthoringCollapsed = () => {},
  getSelectedShotId = () => null,
  syncSelectedShotId = () => {},
  withPreservedScrollState = (_elements, callback) => callback(),
  scrollRenderTargets = () => [],
  applyLayoutState = () => {},
  renderHeader = () => {},
  renderStats = () => {},
  renderVideo = () => {},
  renderWaveform = () => {},
  renderTimingTables = () => {},
  renderLiveOverlay = () => {},
  requestRender = () => {},
  flushPendingInspectorScrollRestore = () => {},
  rememberInspectorScrollPosition = () => {},
  maybeApplyRecommendedLayout = () => {},
  renderShotML = () => {},
  renderCollapsibleInspectorSections = () => {},
  formatSyncOffsetLabel = (value) => String(value ?? ""),
  currentSourceSyncOffsetMs = () => 0,
  projectDetailValue = () => "",
  renderPractiScoreOptionLists = () => {},
  syncControlValue = () => {},
  syncControlChecked = () => {},
  currentPipSizePercent = () => 35,
  overlayBadgeLockedToStack = () => false,
  syncOverlayBubbleSizeControls = () => {},
  syncOverlayCoordinateControlState = () => {},
  syncOverlayBubbleLockControlState = () => {},
  renderTextBoxEditors = () => {},
  renderPopupEditors = () => {},
  syncTimingEventLabelState = () => {},
  syncExportPathControl = () => {},
  renderScoringPresetOptions = () => {},
  renderPractiScoreSummaries = () => {},
  renderExportPresetOptions = () => {},
  renderExportLog = () => {},
  renderSettingsPane = () => {},
  renderMetricsPanel = () => {},
  renderMergeMediaList = () => {},
  renderTrimSyncList = () => {},
  renderOutputProfiles = () => {},
  renderReviewSourceControls = () => {},
  renderReviewImportedMetrics = () => {},
  createOutputProfile = () => {},
  saveOutputProfile = () => {},
  deleteOutputProfile = () => {},
  selectOutputProfile = () => {},
  setReviewSource = () => {},
  exportBadges = () => {},
  scheduleOutputProfileFieldCommit = () => {},
  badgeControls = [],
  badgeDisplayLabels = {},
  scoringColorOptions = () => [],
  bindOverlayColorInput = () => {},
  isColorInput = () => false,
  syncOpacityPercentControl = () => {},
  createNewProject = async () => null,
  hasActiveProject = () => false,
  setStatus = () => {},
  gatedProjectActionMessage = () => "Please create / select project.",
  importTypedPath = async () => null,
  browseProjectPath = async () => null,
  pickPath = async () => "",
  scheduleExportSettingsApply = () => {},
  requireValue = () => "",
  flushPendingProjectDrafts = async () => {},
  callApi = async () => null,
  openHiddenFileInput = () => {},
  postFile = async () => null,
  postFiles = async () => null,
  validatePractiScoreSelection = () => null,
  openPractiScoreDashboard = async () => null,
  syncPractiScoreSelectionFields = () => {},
  schedulePractiScoreContextApply = () => {},
  scheduleProjectDetailsApply = () => {},
  scheduleScoringApply = () => {},
  handleStageFullscreenChange = () => {},
  logPrimaryVideoState = () => {},
  scheduleSecondaryPreviewSync = () => {},
  startOverlayLoop = () => {},
  stopOverlayLoop = () => {},
  renderWaveformPlayhead = () => {},
  setWaveformMode = () => {},
  setWaveformTrackMode = () => {},
  setWaveformExpanded = () => {},
  setWaveformZoom = () => {},
  setWaveformAmplitude = () => {},
  resetWaveformView = () => {},
  setTimingExpanded = () => {},
  setMarkersExpanded = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  setScoringWorkbenchExpanded = () => {},
  setMetricsExpanded = () => {},
  handleWaveformPointerDown = () => {},
  handleWaveformPointerMove = () => {},
  handleWaveformPointerUp = () => {},
  handleWaveformNavigatorPointerDown = () => {},
  handleWaveformWheel = () => {},
  handleKeyboardEdit = () => {},
  handleWindowVisibilityRestore = () => {},
  cancelOverlayDragInteractions = () => {},
  handleViewportLayoutChange = () => {},
  scheduleThresholdApply = () => {},
  applyThresholdNow = async () => null,
  scheduleShotMLSettingsApply = () => {},
  cancelMergeAutoApply = () => {},
  syncMergePreviewStateFromControls = () => {},
  scheduleInteractionPreviewRender = () => {},
  scheduleMergeApply = () => {},
  addTimingEvent = () => {},
  beginOverlayBadgeDrag = () => {},
  beginTextBoxDrag = () => {},
  beginMergePreviewDrag = () => {},
  beginPopupBubbleDrag = () => {},
  syncOverlayFontSizePreset = () => {},
  syncOverlayPreviewStateFromControls = () => {},
  scheduleOverlayApply = () => {},
  resetOverlayPlacementBaseline = () => {},
  ensureShotQuadrantDefaults = () => {},
  commitOverlayControlChanges = () => {},
  previewOverlayControlChanges = () => {},
  addOverlayTextBox = () => {},
  importShotPopups = () => {},
  createPopupBubbleForShot = () => false,
  addPopupBubble = () => {},
  toggleSelectedPopupEditor = () => {},
  setPopupFilterMode = () => {},
  selectAdjacentPopupBubble = () => {},
  popupBubbles = () => [],
  readPopupTemplatePayload = () => ({}),
  scheduleSettingsDefaultsApply = () => {},
  readSettingsDefaultsPayload = () => ({}),
  captureSettingsDraft = () => null,
  clearSettingsDraft = () => {},
  applySettingsDefaults = () => {},
  toggleLayoutLock = () => {},
  resetLayout = () => {},
  beginLayoutResize = () => {},
  moveLayoutResize = () => {},
  endLayoutResize = () => {},
  moveTimingColumnResize = () => {},
  endTimingColumnResize = () => {},
  moveOverlayBadgeDrag = () => {},
  endOverlayBadgeDrag = () => {},
  moveMergePreviewDrag = () => {},
  endMergePreviewDrag = () => {},
  moveTextBoxDrag = () => {},
  endTextBoxDrag = () => {},
  movePopupBubbleDrag = () => {},
  endPopupBubbleDrag = () => {},
  scheduleExportLayoutApply = () => {},
  buildExportPayload = () => ({}),
  applyExportDraft = () => {},
  cancelPendingExportDrafts = () => {},
  flushPendingMergeSourceCommits = async () => {},
  openExportLogModal = () => {},
  downloadExportLog = () => {},
  closeExportLogModal = () => {},
  closeColorPicker = () => {},
  updateColorPickerFromSliders = () => {},
  updateColorPickerFromHexInput = () => {},
  exportMetrics = () => {},
  stopActivityPolling = () => {},
  flushPendingProjectDraftsKeepalive = () => {},
  flushActivityQueue = () => {},
  activity = () => {},
  DEFAULT_PROJECT_UI_STATE = {},
} = {}) {
  let settingsMutationQueue = Promise.resolve();

  function enqueueSettingsMutation(action) {
    const pending = settingsMutationQueue.then(action, action);
    settingsMutationQueue = pending.catch(() => {});
    return pending;
  }

  function currentState() {
    return getState() || {};
  }

  async function saveCurrentSettings(section = null) {
    return enqueueSettingsMutation(async () => {
      const options = {
        projectDefaults: true,
        ...(section ? { section } : {}),
      };
      // Capture layout and other client-owned values before flushing project drafts.
      // Each flush response refreshes remote state and may legitimately synchronize
      // the project snapshot, but it must not replace the values from this click.
      const payload = readSettingsDefaultsPayload(options);
      await flushPendingProjectDrafts();
      await applySettingsDefaults({ ...options, payload });
    });
  }

  function scheduleCurrentSettingsDefaultsApply() {
    const payload = captureSettingsDraft() || readSettingsDefaultsPayload();
    const scheduledGeneration = Number(windowObject.settingsDefaultsApplyGeneration || 0) + 1;
    windowObject.settingsDefaultsApplyGeneration = scheduledGeneration;
    scheduleSettingsDefaultsApply({ payload, scheduledGeneration });
  }

  function renderStyleControls() {
    const state = currentState();
    const project = state?.project;
    const grid = $("badge-style-grid");
    if (!project || !(grid instanceof HTMLElement)) return;
    const badgeKeys = new Set(badgeControls.map(([key]) => key));
    grid.querySelectorAll(".style-card[data-badge]").forEach((card) => {
      const badgeName = card.dataset.badge;
      if (!badgeKeys.has(badgeName)) card.remove();
    });
    badgeControls.forEach(([key, title]) => {
      const style = project.overlay[key];
      let card = grid.querySelector(`.style-card[data-badge="${key}"]`);
      if (!card) {
        card = documentObject.createElement("section");
        card.className = "style-card badge-style-card";
        card.dataset.badge = key;
        card.innerHTML = `
        <h4></h4>
        <label class="color-field"><span class="style-card-label">Bg</span>
          <span class="color-control-pair">
            <button type="button" class="color-swatch-button" data-color-label="Badge background" data-field="background_color"></button>
            <input type="text" class="color-hex-input" inputmode="text" spellcheck="false" aria-label="Background hex value" placeholder="#111827" />
          </span>
        </label>
        <label class="color-field"><span class="style-card-label">Text</span>
          <span class="color-control-pair">
            <button type="button" class="color-swatch-button" data-color-label="Badge text" data-field="text_color"></button>
            <input type="text" class="color-hex-input" inputmode="text" spellcheck="false" aria-label="Text hex value" placeholder="#F9FAFB" />
          </span>
        </label>
        <label class="opacity-field"><span class="style-card-label">Opacity</span>
          <span class="opacity-control-pair">
            <span class="opacity-percent-field">
              <input type="number" class="opacity-percent-input" data-field="opacity" min="0" max="100" step="1" value="90" aria-label="Opacity percent" />
              <span class="opacity-percent-suffix">%</span>
            </span>
          </span>
        </label>
      `;
        bindOverlayColorInput(card.querySelector('[data-field="background_color"]'));
        bindOverlayColorInput(card.querySelector('[data-field="text_color"]'));
        grid.appendChild(card);
      }
      const heading = card.querySelector("h4");
      const displayTitle = badgeDisplayLabels[key] || title.replace(/ Badge$/, "");
      if (heading && heading.textContent !== displayTitle) heading.textContent = displayTitle;
      syncControlValue(card.querySelector('[data-field="background_color"]'), style.background_color);
      syncControlValue(card.querySelector('[data-field="text_color"]'), style.text_color);
      syncOpacityPercentControl(card.querySelector('[data-field="opacity"]'), style.opacity);
    });

    const scoreGrid = $("score-color-grid");
    if (!(scoreGrid instanceof HTMLElement)) return;
    const scoreOptions = scoringColorOptions();
    const scoreKeys = scoreOptions.map((option) => option.key);
    const validLetters = new Set(scoreKeys);
    scoreGrid.querySelectorAll(".score-color-input[data-letter]").forEach((input) => {
      if (!validLetters.has(input.dataset.letter)) {
        input.closest("label")?.remove();
      }
    });
    scoreOptions.forEach((option) => {
      const key = option.key;
      const labelText = option.label || key;
      let input = [...scoreGrid.querySelectorAll(".score-color-input[data-letter]")].find((candidate) => candidate.dataset.letter === key);
      if (!input) {
        const label = documentObject.createElement("label");
        label.className = "color-field score-color-field";
        label.title = option.description || labelText;
        const text = documentObject.createElement("span");
        text.className = "score-color-label";
        text.textContent = labelText;
        label.appendChild(text);
        const pair = documentObject.createElement("span");
        pair.className = "color-control-pair";
        input = documentObject.createElement("button");
        input.type = "button";
        input.className = "score-color-input color-swatch-button";
        input.dataset.letter = key;
        input.dataset.colorLabel = `${labelText} color`;
        const hex = documentObject.createElement("input");
        hex.type = "text";
        hex.className = "color-hex-input";
        hex.inputMode = "text";
        hex.spellcheck = false;
        hex.placeholder = "#FFFFFF";
        pair.append(input, hex);
        label.appendChild(pair);
        scoreGrid.appendChild(label);
        bindOverlayColorInput(input);
      }
      syncControlValue(
        input,
        project.overlay.scoring_colors[key]
        || "#ffffff",
      );
      const label = input.closest("label");
      if (label) label.title = option.description || labelText;
    });
  }

  function renderControls() {
    const state = currentState();
    const project = state?.project;
    if (!project) return;
    renderShotML();
    renderCollapsibleInspectorSections();
    const mergeSources = project.merge_sources || [];
    $("sync-offset").textContent = mergeSources.length === 0
      ? "Defaults only"
      : mergeSources.length === 1
        ? formatSyncOffsetLabel(currentSourceSyncOffsetMs(mergeSources[0]))
        : "Per-source sync";
    syncControlValue($("project-name"), projectDetailValue("name"));
    syncControlValue($("project-description"), projectDetailValue("description"));
    syncControlValue($("project-output-root"), project.output_root || "");
    syncControlValue($("match-type"), project.scoring.match_type || "");
    syncControlChecked($("merge-enabled"), project.merge.enabled);
    syncControlValue($("merge-layout"), project.merge.layout);
    const pipValue = Number(
      project.merge.pip_size_percent
        ?? Number(String(project.merge.pip_size || "35%").replace(/%$/, ""))
        ?? 35,
    );
    syncControlValue($("pip-size"), pipValue);
    $("pip-size-label").textContent = `${pipValue}%`;
    syncControlValue($("pip-x"), project.merge.pip_x ?? 1);
    syncControlValue($("pip-y"), project.merge.pip_y ?? 1);
    const overlayPosition = project.overlay.position || "none";
    if (overlayPosition !== "none") {
      setOverlayVisibilityPosition(overlayPosition);
    } else if (!getOverlayVisibilityPosition() || getOverlayVisibilityPosition() === "none") {
      setOverlayVisibilityPosition(state.settings?.overlay_position || "bottom");
    }
    syncControlChecked($("show-overlay"), overlayPosition !== "none");
    syncControlChecked($("show-markers"), project.ui_state?.review_show_markers ?? DEFAULT_PROJECT_UI_STATE.review_show_markers);
    syncControlChecked($("show-pip"), project.ui_state?.review_show_pip ?? DEFAULT_PROJECT_UI_STATE.review_show_pip);
    syncControlValue($("badge-size"), project.overlay.badge_size);
    setOverlayStyleMode(project.overlay.style_type || getOverlayStyleMode());
    setOverlaySpacing(Number(project.overlay.spacing ?? getOverlaySpacing()));
    setOverlayMargin(Number(project.overlay.margin ?? getOverlayMargin()));
    syncControlValue($("overlay-style"), getOverlayStyleMode());
    syncControlValue($("overlay-spacing"), getOverlaySpacing());
    syncControlValue($("overlay-margin"), getOverlayMargin());
    syncControlValue($("max-visible-shots"), project.overlay.max_visible_shots);
    syncControlValue($("shot-quadrant"), project.overlay.shot_quadrant);
    syncControlValue($("shot-direction"), project.overlay.shot_direction);
    syncControlValue($("overlay-custom-x"), project.overlay.custom_x ?? "");
    syncControlValue($("overlay-custom-y"), project.overlay.custom_y ?? "");
    syncControlValue($("timer-x"), project.overlay.timer_x ?? "");
    syncControlValue($("timer-y"), project.overlay.timer_y ?? "");
    syncControlValue($("draw-x"), project.overlay.draw_x ?? "");
    syncControlValue($("draw-y"), project.overlay.draw_y ?? "");
    syncControlValue($("score-x"), project.overlay.score_x ?? "");
    syncControlValue($("score-y"), project.overlay.score_y ?? "");
    syncControlChecked($("timer-lock-to-stack"), overlayBadgeLockedToStack("timer", project.overlay));
    syncControlChecked($("draw-lock-to-stack"), overlayBadgeLockedToStack("draw", project.overlay));
    syncControlChecked($("score-lock-to-stack"), overlayBadgeLockedToStack("score", project.overlay));
    syncOverlayBubbleSizeControls();
    syncControlValue($("overlay-font-family"), project.overlay.font_family);
    syncControlValue($("overlay-font-size"), project.overlay.font_size);
    syncControlChecked($("overlay-font-bold"), project.overlay.font_bold);
    syncControlChecked($("overlay-font-italic"), project.overlay.font_italic);
    syncControlChecked($("show-timer"), project.overlay.show_timer);
    syncControlChecked($("show-draw"), project.overlay.show_draw);
    syncControlChecked($("show-shots"), project.overlay.show_shots);
    syncControlChecked($("show-shot-scores"), project.overlay.show_shot_scores ?? true);
    syncControlChecked($("show-score"), project.overlay.show_score);
    syncOverlayCoordinateControlState();
    syncOverlayBubbleLockControlState();
    renderTextBoxEditors();
    renderPopupEditors();
    syncTimingEventLabelState();
    syncControlChecked($("scoring-enabled"), project.scoring.enabled);
    syncControlValue($("quality"), project.export.quality);
    syncControlValue($("aspect-ratio"), project.export.aspect_ratio);
    syncControlValue($("target-width"), project.export.target_width ?? "");
    syncControlValue($("target-height"), project.export.target_height ?? "");
    syncControlValue($("frame-rate"), project.export.frame_rate);
    syncControlValue($("video-codec"), project.export.video_codec);
    syncControlValue($("video-bitrate"), project.export.video_bitrate_mbps);
    syncControlValue($("audio-codec"), project.export.audio_codec);
    syncControlValue($("audio-sample-rate"), project.export.audio_sample_rate);
    syncControlValue($("audio-bitrate"), project.export.audio_bitrate_kbps);
    syncControlValue($("audio-output-level"), project.export.audio_output_level_percent ?? 100);
    syncControlValue($("color-space"), project.export.color_space);
    syncControlChecked($("two-pass"), project.export.two_pass);
    syncControlValue($("ffmpeg-preset"), project.export.ffmpeg_preset);
    syncExportPathControl();
    renderScoringPresetOptions();
    renderPractiScoreSummaries();
    renderExportPresetOptions();
    renderExportLog();
    renderSettingsPane();
    renderMetricsPanel();
    renderStyleControls();
    renderMergeMediaList();
    renderTrimSyncList();
    renderReviewImportedMetrics();
  }

  function render() {
    if (!currentState()?.project) return;
    syncSelectedShotId();
    withPreservedScrollState(scrollRenderTargets(), () => {
      applyLayoutState();
      renderHeader();
      renderStats();
      renderVideo();
      renderWaveform();
      renderTimingTables();
      renderControls();
      renderLiveOverlay();
      renderOutputProfiles();
      renderReviewSourceControls();
      setActiveTool(getActiveTool(), { collapseExpandedLayout: false, persistUiState: false });
    });
    flushPendingInspectorScrollRestore();
  }

  function renderViewportLayout() {
    if (!currentState()?.project) return;
    withPreservedScrollState(scrollRenderTargets(), () => {
      maybeApplyRecommendedLayout();
      applyLayoutState();
      renderVideo();
      renderWaveform();
      renderLiveOverlay();
    });
    flushPendingInspectorScrollRestore();
  }

  function wireEvents() {
    documentObject.querySelectorAll("[data-tool]").forEach((item) => {
      item.addEventListener("click", () => {
        activity("ui.tool.click", { tool: item.dataset.tool });
        setActiveTool(item.dataset.tool);
      });
    });
    $("new-project").addEventListener("click", async () => {
      await createNewProject();
    });
    $("browse-project-path").addEventListener("click", browseProjectPath);
    $("open-project").addEventListener("click", browseProjectPath);
    $("browse-project-output-root").addEventListener("click", () => pickPath(
      "project_folder",
      "project-output-root",
      async () => scheduleProjectDetailsApply(),
      currentState()?.project?.path
        ? `${String(currentState().project.path).replace(/[\\/]+$/, "")}/Output`
        : "",
    ));
    $("toggle-rail")?.addEventListener("click", () => {
      const nextRailCollapsed = !getRailCollapsed();
      setRailCollapsed(nextRailCollapsed);
      windowObject.localStorage.setItem("splitshot.railCollapsed", String(nextRailCollapsed));
      requestRender();
    });
    $("primary-file-input").addEventListener("change", async (event) => {
      if (!hasActiveProject()) {
        setStatus(gatedProjectActionMessage());
        event.target.value = "";
        return;
      }
      const selectedFile = event.target.files?.[0] || null;
      if (!selectedFile) {
        event.target.value = "";
        return;
      }
      await flushPendingProjectDrafts({ primaryImport: true });
      const result = await postFile("/api/files/primary", selectedFile);
      if (result) setActiveTool("media");
      event.target.value = "";
    });
    $("merge-media-input").addEventListener("change", async (event) => {
      const files = Array.from(event.target.files || []);
      const result = await postFiles("/api/files/merge", files);
      if (result) setActiveTool("media");
      event.target.value = "";
    });
    $("media-add-more-input").addEventListener("change", async (event) => {
      const files = Array.from(event.target.files || []);
      const result = await postFiles("/api/files/merge", files);
      if (result) setActiveTool("media");
      event.target.value = "";
    });
    $("import-practiscore").addEventListener("click", async () => {
      if (!hasActiveProject()) {
        setStatus(gatedProjectActionMessage());
        return;
      }
      setStatus("Select a PractiScore results file (.csv or .txt).");
      const projectRoot = String(currentState()?.project?.path || "").trim().replace(/[\\/]+$/, "");
      const selectedPath = await pickPath(
        "practiscore",
        null,
        null,
        projectRoot ? `${projectRoot}/CSV` : "",
      );
      if (!selectedPath) return;
      await callApi("/api/import/practiscore", { path: selectedPath });
    });
    $("open-practiscore-dashboard")?.addEventListener("click", async () => {
      if (!hasActiveProject()) {
        setStatus(gatedProjectActionMessage());
        return;
      }
      await openPractiScoreDashboard();
    });
    $("practiscore-file-input").addEventListener("change", async (event) => {
      if (!hasActiveProject()) {
        setStatus(gatedProjectActionMessage());
        event.target.value = "";
        return;
      }
      const selectedFile = event.target.files?.[0] || null;
      if (!selectedFile) {
        event.target.value = "";
        return;
      }
      await postFile("/api/files/practiscore", selectedFile);
      event.target.value = "";
    });
    $("delete-project").addEventListener("click", async () => {
      const projectPath = (currentState()?.project?.path || "").trim();
      if (!projectPath) return;
      const shouldDelete = windowObject.confirm(`Delete project metadata for:\n\n${projectPath}\n\nProject folders and files will be kept on disk.`);
      if (!shouldDelete) return;
      await flushPendingProjectDrafts();
      await callApi("/api/project/delete", {});
    });
    ["project-name", "project-description", "project-output-root"].forEach((id) => {
      $(id).addEventListener("input", scheduleProjectDetailsApply);
    });
    $("match-type")?.addEventListener("change", schedulePractiScoreContextApply);
    $("match-competitor-name")?.addEventListener("change", (event) => {
      syncPractiScoreSelectionFields("match-competitor-name");
      schedulePractiScoreContextApply();
    });
    $("match-competitor-place")?.addEventListener("change", (event) => {
      syncPractiScoreSelectionFields("match-competitor-place");
      schedulePractiScoreContextApply();
    });
    $("match-class")?.addEventListener("change", schedulePractiScoreContextApply);
    $("match-division")?.addEventListener("change", schedulePractiScoreContextApply);
    documentObject.addEventListener("fullscreenchange", handleStageFullscreenChange);
    documentObject.addEventListener("webkitfullscreenchange", handleStageFullscreenChange);
    ["loadedmetadata", "loadeddata"].forEach((eventName) => {
      $("primary-video").addEventListener(eventName, () => {
        logPrimaryVideoState(eventName);
        renderVideo();
        scheduleSecondaryPreviewSync();
        renderLiveOverlay();
      });
      $("secondary-video").addEventListener(eventName, () => {
        scheduleSecondaryPreviewSync();
        renderLiveOverlay();
      });
    });
    $("primary-video").addEventListener("volumechange", () => {
      logPrimaryVideoState("volumechange");
    });
    $("primary-video").addEventListener("canplay", () => {
      logPrimaryVideoState("canplay");
    });
    $("primary-video").addEventListener("error", () => {
      logPrimaryVideoState("error");
    });
    $("primary-video").addEventListener("play", () => {
      logPrimaryVideoState("play");
    });
    $("primary-video").addEventListener("pause", () => {
      logPrimaryVideoState("pause");
    });
    $("primary-video").addEventListener("play", startOverlayLoop);
    $("primary-video").addEventListener("pause", stopOverlayLoop);
    $("primary-video").addEventListener("seeked", () => {
      activity("video.seeked", { current_time_s: $("primary-video").currentTime });
      scheduleSecondaryPreviewSync();
      renderLiveOverlay();
      renderWaveformPlayhead();
      if (getActiveTool() === "markers" && getPopupFilterMode() === "visible") renderPopupEditors();
    });
    $("primary-video").addEventListener("timeupdate", () => {
      if (getOverlayFrame() !== null) return;
      scheduleSecondaryPreviewSync();
      renderLiveOverlay();
      renderWaveformPlayhead();
      if (getActiveTool() === "markers" && getPopupFilterMode() === "visible") renderPopupEditors();
    });
    documentObject.querySelectorAll("[data-waveform-mode]").forEach((button) => {
      button.addEventListener("click", () => setWaveformMode(button.dataset.waveformMode));
    });
    $("expand-waveform").addEventListener("click", () => {
      setWaveformExpanded(!$("cockpit-root").classList.contains("waveform-expanded"));
    });
    $("zoom-waveform-out").addEventListener("click", () => setWaveformZoom(0.5));
    $("zoom-waveform-in").addEventListener("click", () => setWaveformZoom(2));
    $("amp-waveform-out").addEventListener("click", () => setWaveformAmplitude(0.5));
    $("amp-waveform-in").addEventListener("click", () => setWaveformAmplitude(2));
    $("reset-waveform-view").addEventListener("click", resetWaveformView);
    $("waveform-mode-single")?.addEventListener("click", () => setWaveformTrackMode("single"));
    $("waveform-mode-multi")?.addEventListener("click", () => setWaveformTrackMode("multi"));
    $("expand-timing").addEventListener("click", () => setTimingExpanded(true));
    $("collapse-timing").addEventListener("click", () => setTimingExpanded(false));
    $("expand-markers")?.addEventListener("click", () => {
      setActiveTool("markers", { collapseExpandedLayout: false });
      setMarkersExpanded(true);
    });
    $("timing-enabled")?.addEventListener("change", () => {
      syncLocalProjectUiState();
      scheduleProjectUiStateApply();
      renderTimingTables();
    });
    $("expand-scoring")?.addEventListener("click", () => {
      setScoringWorkbenchExpanded(true);
      $("scoring-workbench")?.scrollIntoView({ block: "start" });
    });
    $("collapse-scoring")?.addEventListener("click", () => setScoringWorkbenchExpanded(false));
    $("expand-metrics")?.addEventListener("click", () => setMetricsExpanded(true));
    $("collapse-metrics")?.addEventListener("click", () => setMetricsExpanded(false));
    $("waveform").addEventListener("pointerdown", handleWaveformPointerDown);
    $("waveform").addEventListener("pointermove", handleWaveformPointerMove);
    $("waveform").addEventListener("pointerup", handleWaveformPointerUp);
    $("waveform").addEventListener("pointercancel", handleWaveformPointerUp);
    $("waveform-window-track").addEventListener("pointerdown", handleWaveformNavigatorPointerDown);
    $("waveform").addEventListener("wheel", handleWaveformWheel, { passive: false });
    documentObject.addEventListener("pointermove", handleWaveformPointerMove);
    documentObject.addEventListener("pointerup", handleWaveformPointerUp);
    documentObject.addEventListener("pointercancel", handleWaveformPointerUp);
    documentObject.addEventListener("lostpointercapture", handleWaveformPointerUp);
    documentObject.addEventListener("keydown", handleKeyboardEdit);
    documentObject.addEventListener("visibilitychange", handleWindowVisibilityRestore);
    documentObject.addEventListener("visibilitychange", () => {
      if (documentObject.visibilityState && documentObject.visibilityState !== "visible") {
        cancelOverlayDragInteractions("document.hidden");
      }
    });
    windowObject.addEventListener("resize", handleViewportLayoutChange);
    windowObject.addEventListener("focus", handleWindowVisibilityRestore);
    windowObject.addEventListener("pageshow", handleWindowVisibilityRestore);
    windowObject.addEventListener("blur", () => cancelOverlayDragInteractions("window.blur"));
    windowObject.visualViewport?.addEventListener("resize", handleViewportLayoutChange);
    documentObject.querySelector(".inspector")?.addEventListener("scroll", rememberInspectorScrollPosition, { passive: true });
    $("threshold").addEventListener("input", scheduleThresholdApply);
    $("threshold").addEventListener("change", scheduleThresholdApply);
    $("threshold").addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      scheduleThresholdApply();
    });
    $("apply-threshold").addEventListener("click", applyThresholdNow);
    documentObject.querySelectorAll("[data-shotml-setting]").forEach((input) => {
      if (input.id === "threshold") return;
      input.addEventListener("input", scheduleShotMLSettingsApply);
      input.addEventListener("change", scheduleShotMLSettingsApply);
    });
    $("generate-shotml-proposals").addEventListener("click", () => callApi("/api/analysis/shotml/proposals", {}));
    $("reset-shotml-defaults").addEventListener("click", () => callApi("/api/analysis/shotml/reset-defaults", {}));
    $("restore-merge-defaults")?.addEventListener("click", async () => {
      resetMergeDraft();
      cancelMergeAutoApply();
      const merge = getState()?.project?.merge;
      if (merge) {
        merge.enabled = false;
        merge.layout = "side_by_side";
        merge.pip_size_percent = 35;
        merge.pip_x = 1;
        merge.pip_y = 1;
      }
      if ($("merge-enabled")) $("merge-enabled").checked = false;
      if ($("merge-layout")) $("merge-layout").value = "side_by_side";
      if ($("pip-size")) $("pip-size").value = "35";
      if ($("pip-size-label")) $("pip-size-label").textContent = "35%";
      if ($("pip-x")) $("pip-x").value = "1";
      if ($("pip-y")) $("pip-y").value = "1";
      await callApi("/api/merge/reset-defaults", {});
      scheduleInteractionPreviewRender({ video: true });
    });
    ["merge-enabled", "merge-layout"].forEach((id) => {
      $(id).addEventListener("change", () => {
        syncMergePreviewStateFromControls();
        scheduleInteractionPreviewRender({ video: true });
        scheduleMergeApply();
      });
    });
    $("pip-size").addEventListener("input", () => {
      $("pip-size-label").textContent = `${$("pip-size").value}%`;
      syncMergePreviewStateFromControls();
      scheduleInteractionPreviewRender({ video: true });
      scheduleMergeApply();
    });
    ["pip-x", "pip-y"].forEach((id) => {
      $(id).addEventListener("input", () => {
        syncMergePreviewStateFromControls();
        scheduleInteractionPreviewRender({ video: true });
        scheduleMergeApply();
      });
    });
    documentObject.querySelectorAll("[data-sync]").forEach((button) => {
      button.addEventListener("click", () => callApi("/api/sync", { delta_ms: Number(button.dataset.sync) }));
    });
    $("timing-event-kind").addEventListener("change", syncTimingEventLabelState);
    $("add-timing-event").addEventListener("click", addTimingEvent);
    $("video-stage").addEventListener("pointerdown", beginOverlayBadgeDrag);
    $("video-stage").addEventListener("pointerdown", beginTextBoxDrag, true);
    $("video-stage").addEventListener("mousedown", beginTextBoxDrag, true);
    documentObject.addEventListener("pointerdown", beginTextBoxDrag, true);
    documentObject.addEventListener("mousedown", beginTextBoxDrag, true);
    $("merge-preview-layer").addEventListener("pointerdown", beginMergePreviewDrag);
    $("merge-preview-layer").addEventListener("mousedown", beginMergePreviewDrag);
    $("custom-overlay").addEventListener("pointerdown", beginTextBoxDrag);
    $("popup-overlay")?.addEventListener("pointerdown", beginPopupBubbleDrag);
    $("popup-overlay")?.addEventListener("mousedown", beginPopupBubbleDrag);
    ["badge-size"].forEach((id) => {
      $(id).addEventListener("change", () => {
        syncOverlayFontSizePreset();
        syncOverlayPreviewStateFromControls();
        renderLiveOverlay();
        scheduleOverlayApply();
      });
    });
    [
      "markers-enable",
      "show-markers",
      "show-pip",
    ].forEach((id) => {
      $(id).addEventListener("change", () => {
        if (id === "markers-enable") {
          syncControlChecked($("show-markers"), $("markers-enable")?.checked ?? true);
        } else if (id === "show-markers") {
          syncControlChecked($("markers-enable"), $("show-markers")?.checked ?? true);
        }
        syncLocalProjectUiState();
        scheduleProjectUiStateApply();
        renderVideo();
        renderLiveOverlay();
      });
    });
    [
      "max-visible-shots",
      "show-overlay",
      "shot-quadrant",
      "shot-direction",
      "overlay-custom-x",
      "overlay-custom-y",
      "timer-lock-to-stack",
      "timer-x",
      "timer-y",
      "draw-lock-to-stack",
      "draw-x",
      "draw-y",
      "score-lock-to-stack",
      "score-x",
      "score-y",
      "bubble-width",
      "bubble-height",
      "overlay-font-family",
      "overlay-font-size",
      "overlay-font-bold",
      "overlay-font-italic",
      "show-timer",
      "show-draw",
      "show-shots",
      "show-shot-scores",
      "show-score",
    ].forEach((id) => {
      const eventName = $(id).tagName === "SELECT" || $(id).type === "checkbox" ? "change" : "input";
      $(id).addEventListener(eventName, () => {
        if (id === "shot-quadrant") {
          resetOverlayPlacementBaseline(id);
          syncOverlayCoordinateControlState();
          ensureShotQuadrantDefaults();
        }
        if (id.endsWith("-lock-to-stack")) {
          resetOverlayPlacementBaseline(id);
          syncOverlayBubbleLockControlState();
        }
        commitOverlayControlChanges();
      });
    });
    [
      ["review-add-text-box", "manual"],
      ["review-add-imported-box", "imported_summary"],
      ["review-add-stage-name-box", "stage_name"],
    ].forEach(([id, source]) => {
      $(id)?.addEventListener("click", () => addOverlayTextBox(source));
    });
    $("popup-import-shots")?.addEventListener("click", importShotPopups);
    $("popup-import-shots-workbench")?.addEventListener("click", importShotPopups);
    $("popup-add-selected-shot")?.addEventListener("click", () => {
      if (!createPopupBubbleForShot(getSelectedShotId())) setStatus("Select a shot before adding a shot-linked marker.");
    });
    $("popup-add-selected-shot-workbench")?.addEventListener("click", () => {
      if (!createPopupBubbleForShot(getSelectedShotId())) setStatus("Select a shot before adding a shot-linked marker.");
    });
    $("popup-add-bubble")?.addEventListener("click", addPopupBubble);
    $("popup-add-bubble-workbench")?.addEventListener("click", addPopupBubble);
    $("popup-edit-selected")?.addEventListener("click", () => {
      toggleSelectedPopupEditor({ focus: true });
    });
    $("popup-toggle-authoring")?.addEventListener("click", () => setPopupAuthoringCollapsed(!getPopupAuthoringCollapsed()));
    $("popup-filter")?.addEventListener("change", (event) => setPopupFilterMode(event.target.value));
    $("markers-workbench-filter")?.addEventListener("change", (event) => setPopupFilterMode(event.target.value));
    $("popup-prev-compact")?.addEventListener("click", () => selectAdjacentPopupBubble(-1));
    $("popup-next-compact")?.addEventListener("click", () => selectAdjacentPopupBubble(1));
    $("popup-prev-workbench")?.addEventListener("click", () => selectAdjacentPopupBubble(-1));
    $("popup-next-workbench")?.addEventListener("click", () => selectAdjacentPopupBubble(1));
    [
      "popup-template-content-type",
      "popup-template-text-source",
    ].forEach((id) => $(id)?.addEventListener("change", () => callApi("/api/popups", { popups: popupBubbles(), popup_template: readPopupTemplatePayload() })));
    [
      "popup-template-enabled",
      "popup-template-follow-motion",
    ].forEach((id) => $(id)?.addEventListener("change", () => callApi("/api/popups", { popups: popupBubbles(), popup_template: readPopupTemplatePayload() })));
    [
      "popup-template-duration-s",
      "popup-template-width",
      "popup-template-height",
      "popup-template-opacity",
    ].forEach((id) => {
      $(id)?.addEventListener("change", () => callApi("/api/popups", { popups: popupBubbles(), popup_template: readPopupTemplatePayload() }));
      $(id)?.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        callApi("/api/popups", { popups: popupBubbles(), popup_template: readPopupTemplatePayload() });
      });
    });
    [
      "popup-template-background-color",
      "popup-template-text-color",
    ].forEach((id) => {
      $(id)?.addEventListener("change", () => callApi("/api/popups", { popups: popupBubbles(), popup_template: readPopupTemplatePayload() }));
      $(id)?.addEventListener("blur", () => callApi("/api/popups", { popups: popupBubbles(), popup_template: readPopupTemplatePayload() }));
    });

    $("settings-import-current")?.addEventListener("click", async () => {
      await saveCurrentSettings();
    });
    [
      "settings-default-tool",
      "settings-reopen-last-tool",
      "settings-layout-locked",
      "settings-default-match-type",
      "settings-overlay-position",
      "settings-badge-size",
      "settings-overlay-custom-background-color",
      "settings-overlay-custom-text-color",
      "settings-timer-badge-background-color",
      "settings-timer-badge-text-color",
      "settings-shot-badge-background-color",
      "settings-shot-badge-text-color",
      "settings-current-shot-badge-background-color",
      "settings-current-shot-badge-text-color",
      "settings-hit-factor-badge-background-color",
      "settings-hit-factor-badge-text-color",
      "settings-merge-layout",
      "settings-pip-size",
      "settings-export-quality",
      "settings-export-preset",
      "settings-export-frame-rate",
      "settings-export-video-codec",
      "settings-export-audio-codec",
      "settings-export-color-space",
      "settings-export-two-pass",
      "settings-export-ffmpeg-preset",
      "settings-marker-content-type",
      "settings-marker-text-source",
      "settings-marker-enabled",
      "settings-marker-use-shot-split-duration",
      "settings-marker-motion-mode",
      "settings-marker-background-color",
      "settings-marker-text-color",
      "settings-marker-quadrant",
    ].forEach((id) => $(id)?.addEventListener("change", scheduleCurrentSettingsDefaultsApply));
    $("settings-marker-follow-motion")?.addEventListener("change", () => {
      if ($("settings-marker-motion-mode")) $("settings-marker-motion-mode").value = $("settings-marker-follow-motion").checked ? "guided" : "fixed";
      scheduleCurrentSettingsDefaultsApply();
    });
    [
      "settings-overlay-custom-opacity",
      "settings-timer-badge-opacity",
      "settings-shot-badge-opacity",
      "settings-current-shot-badge-opacity",
      "settings-hit-factor-badge-opacity",
      "settings-merge-pip-x",
      "settings-merge-pip-y",
      "settings-marker-opacity",
      "settings-marker-duration",
      "settings-marker-width",
      "settings-marker-height",
      "settings-layout-rail-width",
      "settings-layout-inspector-width",
      "settings-layout-waveform-height",
    ].forEach((id) => {
      $(id)?.addEventListener("change", scheduleCurrentSettingsDefaultsApply);
      $(id)?.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        scheduleCurrentSettingsDefaultsApply();
      });
    });
    $("settings-shotml-threshold")?.addEventListener("change", scheduleCurrentSettingsDefaultsApply);
    $("settings-shotml-threshold")?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      scheduleCurrentSettingsDefaultsApply();
    });
    $("settings-reset-defaults")?.addEventListener("click", async () => {
      await enqueueSettingsMutation(async () => {
        documentObject.activeElement?.blur?.();
        resetMergeDraft();
        resetExportDraft();
        cancelPendingExportDrafts();
        await flushPendingSettingsDefaults();
        await callApi("/api/settings/reset-defaults", {});
      });
    });
    $("settings-use-current-layout")?.addEventListener("click", async () => {
      await saveCurrentSettings("layout");
    });
    $("settings-release-layout")?.addEventListener("click", async () => {
      await enqueueSettingsMutation(async () => {
        documentObject.activeElement?.blur?.();
        await flushPendingSettingsDefaults();
        await callApi("/api/settings/reset-defaults", {
          scope: "app",
          section: "layout",
        });
      });
    });
    documentObject.querySelectorAll("[data-settings-save-section]").forEach((button) => {
      button.addEventListener("click", async () => {
        const section = button.getAttribute("data-settings-save-section") || "";
        await saveCurrentSettings(section);
      });
    });
    documentObject.querySelectorAll("[data-settings-reset-section]").forEach((button) => {
      button.addEventListener("click", async () => {
        await enqueueSettingsMutation(async () => {
          documentObject.activeElement?.blur?.();
          const section = button.getAttribute("data-settings-reset-section") || "";
          await flushPendingSettingsDefaults();
          await callApi("/api/settings/reset-defaults", {
            scope: "app",
            section,
          });
        });
      });
    });
    $("review-set-source")?.addEventListener("click", setReviewSource);
    $("review-source-select")?.addEventListener("change", renderReviewSourceControls);
    $("export-badges")?.addEventListener("click", exportBadges);
    $("badge-style-grid").addEventListener("input", (event) => {
      const target = event.target;
      if (isColorInput(target)) return;
      previewOverlayControlChanges();
      scheduleOverlayApply();
    });
    $("badge-style-grid").addEventListener("change", (event) => {
      if (isColorInput(event.target)) return;
      commitOverlayControlChanges();
    });
    ["scoring-enabled", "scoring-preset"].forEach((id) => {
      $(id).addEventListener("change", scheduleScoringApply);
    });
    documentObject.querySelectorAll("[data-layout-lock-toggle]").forEach((button) => {
      button.addEventListener("click", toggleLayoutLock);
    });
    $("reset-layout")?.addEventListener("click", resetLayout);
    [
      ["resize-rail", "railWidth"],
      ["resize-sidebar", "inspectorWidth"],
      ["resize-waveform", "waveformHeight"],
    ].forEach(([id, kind]) => {
      const handle = $(id);
      handle.addEventListener("pointerdown", (event) => beginLayoutResize(kind, event));
    });
    documentObject.addEventListener("pointermove", moveLayoutResize);
    documentObject.addEventListener("pointerup", endLayoutResize);
    documentObject.addEventListener("pointercancel", endLayoutResize);
    documentObject.addEventListener("lostpointercapture", endLayoutResize);
    documentObject.addEventListener("pointermove", moveTimingColumnResize);
    documentObject.addEventListener("pointerup", endTimingColumnResize);
    documentObject.addEventListener("pointercancel", endTimingColumnResize);
    documentObject.addEventListener("lostpointercapture", endTimingColumnResize);
    documentObject.addEventListener("pointermove", moveOverlayBadgeDrag);
    documentObject.addEventListener("pointerup", endOverlayBadgeDrag);
    documentObject.addEventListener("pointercancel", endOverlayBadgeDrag);
    documentObject.addEventListener("lostpointercapture", endOverlayBadgeDrag);
    documentObject.addEventListener("pointermove", moveMergePreviewDrag);
    documentObject.addEventListener("pointerup", endMergePreviewDrag);
    documentObject.addEventListener("pointercancel", endMergePreviewDrag);
    documentObject.addEventListener("lostpointercapture", endMergePreviewDrag);
    documentObject.addEventListener("mousemove", moveMergePreviewDrag);
    documentObject.addEventListener("mouseup", endMergePreviewDrag);
    documentObject.addEventListener("pointermove", moveTextBoxDrag);
    documentObject.addEventListener("pointerup", endTextBoxDrag);
    documentObject.addEventListener("pointercancel", endTextBoxDrag);
    documentObject.addEventListener("lostpointercapture", endTextBoxDrag);
    documentObject.addEventListener("mousemove", moveTextBoxDrag);
    documentObject.addEventListener("mouseup", endTextBoxDrag);
    documentObject.addEventListener("pointermove", movePopupBubbleDrag);
    documentObject.addEventListener("pointerup", endPopupBubbleDrag);
    documentObject.addEventListener("mousemove", movePopupBubbleDrag);
    documentObject.addEventListener("mouseup", endPopupBubbleDrag);
    documentObject.addEventListener("pointercancel", endPopupBubbleDrag);
    documentObject.addEventListener("lostpointercapture", endPopupBubbleDrag);
    ["overlay-style"].forEach((id) => {
      $(id).addEventListener("change", () => {
        setOverlayStyleMode($(id).value);
        syncOverlayPreviewStateFromControls();
        renderLiveOverlay();
        scheduleOverlayApply();
      });
    });
    ["overlay-spacing", "overlay-margin"].forEach((id) => {
      $(id).addEventListener("input", () => {
        const value = Number($(id).value);
        if (id === "overlay-spacing") {
          setOverlaySpacing(value);
        } else {
          setOverlayMargin(value);
        }
        syncOverlayPreviewStateFromControls();
        renderLiveOverlay();
        scheduleOverlayApply();
      });
    });
    ["quality", "aspect-ratio"].forEach((id) => {
      $(id).addEventListener("change", scheduleExportLayoutApply);
    });
    $("create-output-profile")?.addEventListener("click", createOutputProfile);
    $("save-output-profile")?.addEventListener("click", saveOutputProfile);
    $("delete-output-profile")?.addEventListener("click", deleteOutputProfile);
    $("output-profile-select")?.addEventListener("change", () => {
      selectOutputProfile();
      renderReviewSourceControls();
    });
    ["output-profile-name", "output-profile-type", "output-profile-frame"].forEach((id) => {
      $(id)?.addEventListener("change", scheduleOutputProfileFieldCommit);
      $(id)?.addEventListener("input", scheduleOutputProfileFieldCommit);
    });
    $("export-preset").addEventListener("change", () => {
      resetExportDraft();
      activity("auto_apply.export_preset", { preset: $("export-preset").value });
      callApi("/api/export/preset", { preset: $("export-preset").value });
    });
    [
      "target-width",
      "target-height",
      "video-bitrate",
      "audio-sample-rate",
      "audio-bitrate",
      "audio-output-level",
    ].forEach((id) => {
      $(id).addEventListener("input", scheduleExportSettingsApply);
    });
    [
      "frame-rate",
      "video-codec",
      "audio-codec",
      "color-space",
      "ffmpeg-preset",
      "two-pass",
    ].forEach((id) => {
      $(id).addEventListener("change", scheduleExportSettingsApply);
    });
    $("export-export-log")?.addEventListener("click", downloadExportLog);
    $("close-export-log")?.addEventListener("click", closeExportLogModal);
    $("close-color-picker")?.addEventListener("click", () => closeColorPicker({ commit: true }));
    documentObject.querySelectorAll("[data-close-color-picker]").forEach((element) => {
      element.addEventListener("click", () => closeColorPicker({ commit: true }));
    });
    ["color-picker-hue", "color-picker-saturation", "color-picker-lightness"].forEach((id) => {
      $(id)?.addEventListener("input", () => updateColorPickerFromSliders({ commit: false }));
      $(id)?.addEventListener("change", () => updateColorPickerFromSliders({ commit: true }));
    });
    $("color-picker-hex")?.addEventListener("input", () => updateColorPickerFromHexInput({ commit: false }));
    $("color-picker-hex")?.addEventListener("change", () => updateColorPickerFromHexInput({ commit: true }));
    $("color-picker-hex")?.addEventListener("blur", () => updateColorPickerFromHexInput({ commit: true }));
    documentObject.querySelectorAll("[data-close-export-log]").forEach((element) => {
      element.addEventListener("click", closeExportLogModal);
    });
    $("metrics-export-csv")?.addEventListener("click", () => exportMetrics("csv"));
    $("metrics-export-text")?.addEventListener("click", () => exportMetrics("text"));
    windowObject.addEventListener("beforeunload", () => {
      stopActivityPolling();
      flushPendingProjectDraftsKeepalive();
      flushActivityQueue();
    });
    windowObject.addEventListener("pagehide", () => {
      flushPendingProjectDraftsKeepalive();
    });
    documentObject.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !$("color-picker-modal")?.hidden) {
        closeColorPicker({ commit: true });
        return;
      }
      if (event.key === "Escape" && !$("export-log-modal")?.hidden) {
        closeExportLogModal();
      }
    });
  }

  return Object.freeze({
    render,
    renderViewportLayout,
    renderControls,
    renderStyleControls,
    wireEvents,
  });
}
