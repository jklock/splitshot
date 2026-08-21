export function createSettingsPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  getState = () => null,
  getSettingsSectionExpansion = () => new Map(),
  syncControlValue = () => {},
  syncControlChecked = () => {},
  readNumberSetting = (_id, defaultValue) => defaultValue,
  readProjectUiStatePayload = () => ({}),
  normalizePopupTemplate = (template = {}) => template,
  renderExportPresetOptions = () => {},
  ensureSectionToggle = () => {},
} = {}) {
  let settingsDraft = null;

  function currentState() {
    return getState() || {};
  }

  function currentSettings() {
    return currentState().settings || {};
  }

  function settingsSectionExpansion() {
    return getSettingsSectionExpansion() || new Map();
  }

  function settingsPaneIsActive() {
    return documentObject.querySelector('[data-tool-pane="settings"]')?.classList.contains("active") === true;
  }

  function opacityPercent(value, fallback = 0.9) {
    const numeric = Number(value);
    return Math.round(Math.max(0, Math.min(1, Number.isFinite(numeric) ? numeric : fallback)) * 100);
  }

  function readOpacitySetting(id, fallback = 0.9) {
    return Math.max(0, Math.min(1, readNumberSetting(id, opacityPercent(fallback)) / 100));
  }

  function syncSettingsBadgeStyle(prefix, style = {}) {
    syncControlValue($(`${prefix}-background-color`), style.background_color ?? "#000000");
    syncControlValue($(`${prefix}-text-color`), style.text_color ?? "#ffffff");
    syncControlValue($(`${prefix}-opacity`), opacityPercent(style.opacity));
  }

  function readSettingsBadgeStyle(prefix) {
    return {
      background_color: $(`${prefix}-background-color`)?.value || "#000000",
      text_color: $(`${prefix}-text-color`)?.value || "#ffffff",
      opacity: readOpacitySetting(`${prefix}-opacity`),
    };
  }

  function syncSettingsMarkerTemplate(template = {}) {
    syncControlChecked($("settings-marker-enabled"), Boolean(template.enabled ?? true));
    syncControlValue($("settings-marker-content-type"), template.content_type ?? "text");
    syncControlValue($("settings-marker-text-source"), template.text_source ?? "score");
    syncControlValue($("settings-marker-duration"), (Number(template.duration_ms ?? 1000) / 1000).toFixed(3));
    syncControlChecked($("settings-marker-use-shot-split-duration"), Boolean(template.use_shot_split_duration ?? false));
    syncControlValue($("settings-marker-width"), template.width ?? 0);
    syncControlValue($("settings-marker-height"), template.height ?? 0);
    syncControlChecked($("settings-marker-follow-motion"), Boolean(template.follow_motion ?? false));
    syncControlValue($("settings-marker-motion-mode"), Boolean(template.follow_motion ?? false) ? "guided" : "fixed");
    syncControlValue($("settings-marker-quadrant"), template.quadrant ?? "middle_middle");
    syncControlValue($("settings-marker-background-color"), template.background_color ?? "#000000");
    syncControlValue($("settings-marker-text-color"), template.text_color ?? "#ffffff");
    syncControlValue($("settings-marker-opacity"), opacityPercent(template.opacity));
  }

  function settingsValueAtPath(value, path) {
    let current = value;
    for (const key of path) {
      if (!(current && typeof current === "object" && key in current)) return undefined;
      current = current[key];
    }
    return current;
  }

  function settingsHasPath(value, path) {
    let current = value;
    for (const key of path) {
      if (!(current && typeof current === "object" && key in current)) return false;
      current = current[key];
    }
    return true;
  }

  function sameSettingsValue(left, right) {
    return JSON.stringify(left) === JSON.stringify(right);
  }

  function settingsSubsetMatches(actual, expected) {
    if (Array.isArray(expected)) return sameSettingsValue(actual, expected);
    if (expected && typeof expected === "object") {
      if (!(actual && typeof actual === "object")) return false;
      return Object.entries(expected).every(([key, value]) => settingsSubsetMatches(actual[key], value));
    }
    return actual === expected;
  }

  function captureSettingsDraft() {
    if (!settingsPaneIsActive()) return null;
    settingsDraft = readSettingsDefaultsPayload();
    return settingsDraft;
  }

  function clearSettingsDraft() {
    settingsDraft = null;
  }

  function sanitizeMergeSourceDefaults(mergeSources = []) {
    return (Array.isArray(mergeSources) ? mergeSources : [])
      .filter((source) => source && typeof source === "object")
      .map((source) => ({
        asset: { ...(source.asset || {}) },
        pip_size_percent: source.pip_size_percent ?? null,
        pip_x: Number(source.pip_x ?? 1.0),
        pip_y: Number(source.pip_y ?? 1.0),
        opacity: Number(source.opacity ?? 1.0),
        sync_offset_ms: Number(source.sync_offset_ms ?? 0),
      }));
  }

  function sectionSettingsPayload(section, { projectDefaults = false } = {}) {
    const state = currentState();
    const projectOverlay = state?.project?.overlay || {};
    const projectExport = state?.project?.export || {};
    const projectScoring = state?.project?.scoring || {};
    const projectAnalysis = state?.project?.analysis || {};
    const projectMerge = state?.project?.merge || {};
    const projectPopupTemplate = normalizePopupTemplate(state?.project?.popup_template || {});
    const projectUiState = readProjectUiStatePayload() || state?.project?.ui_state || {};
    const timerBadge = projectDefaults ? (projectOverlay.timer_badge || {}) : readSettingsBadgeStyle("settings-timer-badge");
    const shotBadge = projectDefaults ? (projectOverlay.shot_badge || {}) : readSettingsBadgeStyle("settings-shot-badge");
    const currentShotBadge = projectDefaults ? (projectOverlay.current_shot_badge || {}) : readSettingsBadgeStyle("settings-current-shot-badge");
    const hitFactorBadge = projectDefaults ? (projectOverlay.hit_factor_badge || {}) : readSettingsBadgeStyle("settings-hit-factor-badge");
    const markerTemplate = projectDefaults
      ? projectPopupTemplate
      : normalizePopupTemplate({
        enabled: $("settings-marker-enabled")?.checked ?? true,
        content_type: $("settings-marker-content-type")?.value || "text",
        text_source: $("settings-marker-text-source")?.value || "score",
        duration_ms: Math.max(1, Math.round((Number($("settings-marker-duration")?.value || 1) || 1) * 1000)),
        use_shot_split_duration: $("settings-marker-use-shot-split-duration")?.checked ?? false,
        quadrant: $("settings-marker-quadrant")?.value || projectPopupTemplate.quadrant || "middle_middle",
        width: Number($("settings-marker-width")?.value || 0),
        height: Number($("settings-marker-height")?.value || 0),
        follow_motion: $("settings-marker-follow-motion")?.checked ?? false,
        motion_mode: $("settings-marker-motion-mode")?.value || projectPopupTemplate.motion_mode,
        background_color: $("settings-marker-background-color")?.value || "#000000",
        text_color: $("settings-marker-text-color")?.value || "#ffffff",
        opacity: readOpacitySetting("settings-marker-opacity"),
      });
    const payloads = {
      "global-template": {
        default_tool: $("settings-default-tool")?.value || "project",
        reopen_last_tool: $("settings-reopen-last-tool")?.checked ?? true,
      },
      layout: {
        layout_locked: projectDefaults ? Boolean(projectUiState.layout_locked ?? true) : ($("settings-layout-locked")?.checked ?? true),
        layout_rail_width: projectDefaults ? Number(projectUiState.rail_width ?? 84) : readNumberSetting("settings-layout-rail-width", 84),
        layout_inspector_width: projectDefaults ? Number(projectUiState.inspector_width ?? 440) : readNumberSetting("settings-layout-inspector-width", 440),
        layout_waveform_height: projectDefaults ? Number(projectUiState.waveform_height ?? 206) : readNumberSetting("settings-layout-waveform-height", 206),
      },
      scoring: {
        default_match_type: projectDefaults ? (projectScoring.match_type || "uspsa") : ($("settings-default-match-type")?.value || "uspsa"),
      },
      pip: {
        merge_layout: projectDefaults ? (projectMerge.layout || "side_by_side") : ($("settings-merge-layout")?.value || "side_by_side"),
        pip_size: projectDefaults ? (projectMerge.pip_size || "35%") : ($("settings-pip-size")?.value || "35%"),
        merge_pip_x: projectDefaults ? (projectMerge.pip_x ?? 1.0) : readNumberSetting("settings-merge-pip-x", 1.0),
        merge_pip_y: projectDefaults ? (projectMerge.pip_y ?? 1.0) : readNumberSetting("settings-merge-pip-y", 1.0),
        merge_source_defaults: projectDefaults ? sanitizeMergeSourceDefaults(state?.project?.merge_sources || []) : undefined,
      },
      overlay: {
        overlay_position: projectDefaults ? (projectOverlay.position || "bottom") : ($("settings-overlay-position")?.value || "bottom"),
        badge_size: projectDefaults ? (projectOverlay.badge_size || "M") : ($("settings-badge-size")?.value || "M"),
        overlay_custom_box_background_color: projectDefaults ? (projectOverlay.custom_box_background_color || "#000000") : ($("settings-overlay-custom-background-color")?.value || "#000000"),
        overlay_custom_box_text_color: projectDefaults ? (projectOverlay.custom_box_text_color || "#ffffff") : ($("settings-overlay-custom-text-color")?.value || "#ffffff"),
        overlay_custom_box_opacity: projectDefaults ? (projectOverlay.custom_box_opacity ?? 0.9) : readOpacitySetting("settings-overlay-custom-opacity"),
        timer_badge: timerBadge,
        shot_badge: shotBadge,
        current_shot_badge: currentShotBadge,
        hit_factor_badge: hitFactorBadge,
      },
      markers: {
        marker_template: markerTemplate,
      },
      export: {
        export_quality: projectDefaults ? (projectExport.quality || "high") : ($("settings-export-quality")?.value || "high"),
        export_preset: projectDefaults ? (projectExport.preset || "source") : ($("settings-export-preset")?.value || "source"),
        export_frame_rate: projectDefaults ? (projectExport.frame_rate || "source") : ($("settings-export-frame-rate")?.value || "source"),
        export_video_codec: projectDefaults ? (projectExport.video_codec || "h264") : ($("settings-export-video-codec")?.value || "h264"),
        export_audio_codec: projectDefaults ? (projectExport.audio_codec || "aac") : ($("settings-export-audio-codec")?.value || "aac"),
        export_color_space: projectDefaults ? (projectExport.color_space || "bt709_sdr") : ($("settings-export-color-space")?.value || "bt709_sdr"),
        export_two_pass: projectDefaults ? Boolean(projectExport.two_pass ?? false) : ($("settings-export-two-pass")?.checked ?? false),
        export_ffmpeg_preset: projectDefaults ? (projectExport.ffmpeg_preset || "medium") : ($("settings-export-ffmpeg-preset")?.value || "medium"),
      },
      shotml: {
        detection_threshold: projectDefaults
          ? (projectAnalysis?.shotml_settings?.detection_threshold ?? 0.35)
          : readNumberSetting("settings-shotml-threshold", 0.35),
      },
    };
    return Object.fromEntries(Object.entries(payloads[section] || {}).filter(([, value]) => value !== undefined));
  }

  function isSettingsSectionExpanded(sectionId) {
    if (settingsSectionExpansion().has(sectionId)) return Boolean(settingsSectionExpansion().get(sectionId));
    return false;
  }

  function setSettingsSectionExpanded(sectionId, expanded) {
    if (!sectionId) return;
    settingsSectionExpansion().set(sectionId, Boolean(expanded));
  }

  function renderSettingsSections() {
    documentObject.querySelectorAll("[data-settings-section]").forEach((section) => {
      if (!(section instanceof HTMLElement)) return;
      const sectionId = section.dataset.settingsSection || "";
      const expanded = isSettingsSectionExpanded(sectionId);
      section.classList.toggle("collapsed", !expanded);
      ensureSectionToggle(section, expanded, () => {
        setSettingsSectionExpanded(sectionId, !expanded);
        renderSettingsSections();
      });
    });
  }

  function renderSettingsPane() {
    const state = currentState();
    const layers = state?.settings_layers || {};
    const hasProjectPath = Boolean(state?.project?.path);
    const folderSettingsError = String(layers?.project?.folder_settings_error || "").trim();
    const projectOverlay = state?.project?.overlay || {};
    const projectExport = state?.project?.export || {};
    const projectScoring = state?.project?.scoring || {};
    const projectAnalysis = state?.project?.analysis || {};

    const scopeSelect = $("settings-scope");
    const scopeStatus = $("settings-scope-status");
    if (scopeSelect) {
      const folderOption = scopeSelect.querySelector('option[value="folder"]');
      if (folderOption) folderOption.disabled = !hasProjectPath;
      if (!hasProjectPath && scopeSelect.value === "folder") syncControlValue(scopeSelect, "app");
      if (hasProjectPath && !scopeSelect.value) syncControlValue(scopeSelect, "folder");
    }
    const selectedScope = scopeSelect?.value === "folder" && hasProjectPath ? "folder" : "app";
    const persistedSettings = selectedScope === "folder"
      ? (Object.keys(layers.folder || {}).length > 0 ? (layers.folder || {}) : (layers.app || {}))
      : (layers.app || {});
    if (settingsDraft?.scope === selectedScope && settingsSubsetMatches(persistedSettings, settingsDraft.settings)) {
      settingsDraft = null;
    }
    const displayedSettings = settingsDraft?.scope === selectedScope
      ? settingsDraft.settings
      : persistedSettings;
    if (scopeStatus) {
      scopeStatus.textContent = folderSettingsError
        ? folderSettingsError
        : "";
    }

    const shotmlDefaults = displayedSettings.shotml_defaults || {};
    const markerTemplate = normalizePopupTemplate(displayedSettings.marker_template || state?.project?.popup_template || {});

    renderExportPresetOptions("settings-export-preset", null, displayedSettings.export_preset ?? projectExport.preset ?? "source");
    syncControlValue($("settings-default-match-type"), displayedSettings.default_match_type ?? projectScoring.match_type ?? "uspsa");
    syncControlValue($("settings-overlay-position"), displayedSettings.overlay_position ?? state?.project?.overlay?.position ?? "bottom");
    syncControlValue($("settings-badge-size"), displayedSettings.badge_size ?? state?.project?.overlay?.badge_size ?? "M");
    syncControlValue($("settings-overlay-custom-background-color"), displayedSettings.overlay_custom_box_background_color ?? projectOverlay.custom_box_background_color ?? "#000000");
    syncControlValue($("settings-overlay-custom-text-color"), displayedSettings.overlay_custom_box_text_color ?? projectOverlay.custom_box_text_color ?? "#ffffff");
    syncControlValue($("settings-overlay-custom-opacity"), opacityPercent(displayedSettings.overlay_custom_box_opacity ?? projectOverlay.custom_box_opacity));
    syncSettingsBadgeStyle("settings-timer-badge", displayedSettings.timer_badge || projectOverlay.timer_badge || {});
    syncSettingsBadgeStyle("settings-shot-badge", displayedSettings.shot_badge || projectOverlay.shot_badge || {});
    syncSettingsBadgeStyle("settings-current-shot-badge", displayedSettings.current_shot_badge || projectOverlay.current_shot_badge || {});
    syncSettingsBadgeStyle("settings-hit-factor-badge", displayedSettings.hit_factor_badge || projectOverlay.hit_factor_badge || {});
    syncControlValue($("settings-merge-layout"), displayedSettings.merge_layout ?? state?.project?.merge?.layout ?? "side_by_side");
    syncControlValue($("settings-pip-size"), displayedSettings.pip_size ?? state?.project?.merge?.pip_size ?? "35%");
    syncControlValue($("settings-merge-pip-x"), displayedSettings.merge_pip_x ?? state?.project?.merge?.pip_x ?? 1.0);
    syncControlValue($("settings-merge-pip-y"), displayedSettings.merge_pip_y ?? state?.project?.merge?.pip_y ?? 1.0);
    syncControlValue($("settings-export-quality"), displayedSettings.export_quality ?? state?.project?.export?.quality ?? "high");
    syncControlValue($("settings-export-frame-rate"), displayedSettings.export_frame_rate ?? projectExport.frame_rate ?? "source");
    syncControlValue($("settings-export-video-codec"), displayedSettings.export_video_codec ?? projectExport.video_codec ?? "h264");
    syncControlValue($("settings-export-audio-codec"), displayedSettings.export_audio_codec ?? projectExport.audio_codec ?? "aac");
    syncControlValue($("settings-export-color-space"), displayedSettings.export_color_space ?? projectExport.color_space ?? "bt709_sdr");
    syncControlChecked($("settings-export-two-pass"), Boolean(displayedSettings.export_two_pass ?? projectExport.two_pass ?? false));
    syncControlValue($("settings-export-ffmpeg-preset"), displayedSettings.export_ffmpeg_preset ?? projectExport.ffmpeg_preset ?? "medium");
    syncControlValue($("settings-default-tool"), displayedSettings.default_tool ?? "project");
    syncControlChecked($("settings-reopen-last-tool"), Boolean(displayedSettings.reopen_last_tool ?? true));
    syncControlChecked($("settings-layout-locked"), Boolean(displayedSettings.layout_locked ?? state?.project?.ui_state?.layout_locked ?? true));
    syncControlValue($("settings-layout-rail-width"), displayedSettings.layout_rail_width ?? state?.project?.ui_state?.rail_width ?? 84);
    syncControlValue($("settings-layout-inspector-width"), displayedSettings.layout_inspector_width ?? state?.project?.ui_state?.inspector_width ?? 440);
    syncControlValue($("settings-layout-waveform-height"), displayedSettings.layout_waveform_height ?? state?.project?.ui_state?.waveform_height ?? 206);
    syncControlValue(
      $("settings-shotml-threshold"),
      Number(
        settingsDraft?.scope === selectedScope
          ? displayedSettings.detection_threshold
          : shotmlDefaults.detection_threshold
            ?? displayedSettings.detection_threshold
            ?? projectAnalysis?.shotml_settings?.detection_threshold
            ?? 0.35,
      ),
    );
    syncSettingsMarkerTemplate(markerTemplate);
    const markerSource = $("settings-marker-source");
    if (markerSource) {
      markerSource.textContent = hasProjectPath
        ? (Object.keys(layers.folder || {}).length > 0 ? "Folder template" : "Project template")
        : "App template";
    }
    const layoutStatus = $("settings-layout-status");
    if (layoutStatus) {
      layoutStatus.textContent = "";
    }
    const layoutSummary = $("settings-layout-summary");
    if (layoutSummary) {
      layoutSummary.textContent = "";
    }
    const pipSummary = $("settings-pip-summary");
    if (pipSummary) {
      pipSummary.textContent = "";
    }
    renderSettingsSections();

    if (!settingsPaneIsActive()) {
      settingsDraft = null;
    }
  }

  function readSettingsDefaultsPayload({ projectDefaults = false, section = null } = {}) {
    const sectionName = String(section || "").trim().toLowerCase();
    const settings = sectionName
      ? sectionSettingsPayload(sectionName, { projectDefaults })
      : {
        ...sectionSettingsPayload("global-template", { projectDefaults }),
        ...sectionSettingsPayload("layout", { projectDefaults }),
        ...sectionSettingsPayload("scoring", { projectDefaults }),
        ...sectionSettingsPayload("pip", { projectDefaults }),
        ...sectionSettingsPayload("overlay", { projectDefaults }),
        ...sectionSettingsPayload("markers", { projectDefaults }),
        ...sectionSettingsPayload("export", { projectDefaults }),
        ...sectionSettingsPayload("shotml", { projectDefaults }),
      };
    return {
      scope: $("settings-scope")?.value || "app",
      section: sectionName || undefined,
      project_defaults: Boolean(projectDefaults),
      settings,
    };
  }

  return Object.freeze({
    syncSettingsBadgeStyle,
    readSettingsBadgeStyle,
    syncSettingsMarkerTemplate,
    settingsValueAtPath,
    settingsHasPath,
    sameSettingsValue,
    captureSettingsDraft,
    clearSettingsDraft,
    renderSettingsPane,
    isSettingsSectionExpanded,
    setSettingsSectionExpanded,
    renderSettingsSections,
    readSettingsDefaultsPayload,
  });
}
