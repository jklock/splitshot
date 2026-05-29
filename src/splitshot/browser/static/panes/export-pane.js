export function readSharedExportPayload({
  $ = (id) => document.getElementById(id),
  getState = () => null,
  getExportPathDraft = () => "",
} = {}) {
  const state = getState() || {};
  const projectExport = state?.project?.export || {};
  const outputPath = $("export-path")?.value.trim()
    || getExportPathDraft().trim()
    || projectExport.output_path
    || "";
  return {
    preset: $("export-preset")?.value || projectExport.preset || "custom",
    quality: $("quality")?.value || projectExport.quality || "high",
    aspect_ratio: $("aspect-ratio")?.value || projectExport.aspect_ratio || "original",
    output_path: outputPath,
    target_width: $("target-width")?.value ? Number($("target-width").value) : "",
    target_height: $("target-height")?.value ? Number($("target-height").value) : "",
    frame_rate: $("frame-rate")?.value || projectExport.frame_rate || "source",
    video_codec: $("video-codec")?.value || projectExport.video_codec || "h264",
    video_bitrate_mbps: Number($("video-bitrate")?.value || projectExport.video_bitrate_mbps || 15),
    audio_codec: $("audio-codec")?.value || projectExport.audio_codec || "aac",
    audio_sample_rate: Number($("audio-sample-rate")?.value || projectExport.audio_sample_rate || 48000),
    audio_bitrate_kbps: Number($("audio-bitrate")?.value || projectExport.audio_bitrate_kbps || 320),
    color_space: $("color-space")?.value || projectExport.color_space || "bt709_sdr",
    two_pass: $("two-pass")?.checked ?? Boolean(projectExport.two_pass),
    ffmpeg_preset: $("ffmpeg-preset")?.value || projectExport.ffmpeg_preset || "medium",
  };
}

export function createExportPane({
  $ = (id) => document.getElementById(id),
  getState = () => null,
  getExportPathDraft = () => "",
  setExportPathDraft = () => {},
  getExportLogLines = () => [],
  getActiveProcessingPath = () => null,
  getProcessingProgressPercent = () => 0,
  metricsFileStem = () => "splitshot",
  downloadTextFile = () => {},
  setStatus = () => {},
  applyExportDraft = () => {},
  autoApplyExportLayout = () => {},
  autoApplyExportSettings = () => {},
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function persistedExportLogLines() {
    return ((currentState()?.project?.export?.last_log) || "")
      .split(/\r?\n/)
      .filter(Boolean);
  }

  function visibleExportLogLines() {
    const visibleLines = getExportLogLines() || [];
    return visibleLines.length > 0 ? visibleLines : persistedExportLogLines();
  }

  function renderExportPresetOptions(selectId = "export-preset", descriptionId = "export-preset-description", selectedValue = currentState()?.project?.export?.preset) {
    const select = $(selectId);
    if (!select) return;
    select.innerHTML = "";
    (currentState().export_presets || []).forEach((preset) => {
      const option = document.createElement("option");
      option.value = preset.id;
      option.textContent = preset.name;
      select.appendChild(option);
    });
    const custom = document.createElement("option");
    custom.value = "custom";
    custom.textContent = "Custom";
    select.appendChild(custom);
    const hasSelected = Array.from(select.options).some((option) => option.value === selectedValue);
    select.value = hasSelected ? selectedValue : "custom";
    if (descriptionId) {
      const preset = (currentState().export_presets || []).find((item) => item.id === select.value);
      let description = $(descriptionId);
      if (!description) {
        description = document.createElement("div");
        description.id = descriptionId;
        description.className = "hint export-preset-description";
        select.closest("label")?.insertAdjacentElement("afterend", description);
      }
      if (description) {
        description.textContent = preset ? (preset.description || "") : "";
        description.hidden = !Boolean(description.textContent.trim());
      }
    }
  }

  function renderExportLog() {
    const visibleLines = visibleExportLogLines();
    const projectExport = currentState()?.project?.export || {};
    const output = $("export-log-output");
    const summary = $("export-log-summary");
    const errorBox = $("export-log-error");
    const status = $("export-log-status");
    const button = $("show-export-log");
    const exportButton = $("export-export-log");
    if (output) {
      output.textContent = visibleLines.join("\n") || "No export log yet.";
      if (getActiveProcessingPath() === "/api/export") output.scrollTop = output.scrollHeight;
    }
    if (summary) {
      summary.textContent = getActiveProcessingPath() === "/api/export"
        ? `Export in progress • ${Math.round(getProcessingProgressPercent())}%`
        : (visibleLines.length > 0 ? "Most recent local export output." : "No export activity yet.");
    }
    if (errorBox) {
      errorBox.hidden = !projectExport.last_error;
      errorBox.textContent = projectExport.last_error || "";
    }
    if (status) {
      status.textContent = projectExport.last_error
        ? `Latest export failed: ${projectExport.last_error}`
        : getActiveProcessingPath() === "/api/export"
          ? `Export log is updating in real time. Current progress: ${Math.round(getProcessingProgressPercent())}%.`
          : (visibleLines.length > 0 ? "" : "No export log yet.");
      status.hidden = !Boolean(status.textContent);
    }
    if (button) {
      button.textContent = getActiveProcessingPath() === "/api/export"
        ? `Show Log (${Math.round(getProcessingProgressPercent())}%)`
        : "Show Log";
    }
    if (exportButton) exportButton.disabled = visibleLines.length === 0;
  }

  function openExportLogModal() {
    const modal = $("export-log-modal");
    if (!modal) return;
    modal.hidden = false;
    renderExportLog();
    const output = $("export-log-output");
    if (output) output.scrollTop = output.scrollHeight;
  }

  function closeExportLogModal() {
    const modal = $("export-log-modal");
    if (!modal) return;
    modal.hidden = true;
  }

  function downloadExportLog() {
    const visibleLines = visibleExportLogLines();
    if (visibleLines.length === 0) {
      setStatus("No export log available yet.");
      return;
    }
    downloadTextFile(`${metricsFileStem()}-export-log.txt`, `${visibleLines.join("\n")}\n`, "text/plain");
    setStatus("Downloaded export log.");
  }

  function syncExportPathControl() {
    const input = $("export-path");
    if (!input) return;
    const state = currentState();
    const savedPath = state?.project?.export?.output_path || "";
    const defaultPath = state?.project?.path
      ? `${state.project.path}/Output/output.mp4`
      : `${state?.default_project_path || "~/splitshot"}/output.mp4`;
    const draftPath = getExportPathDraft().trim();
    const hasUnsavedDraft = draftPath && draftPath !== savedPath;
    const nextValue = hasUnsavedDraft ? getExportPathDraft() : savedPath || draftPath || input.value || defaultPath;
    if (input.value !== nextValue) input.value = nextValue;
    if (!draftPath) setExportPathDraft(nextValue);
  }

  function readExportLayoutPayload() {
    const payload = readSharedExportPayload({
      $,
      getState: currentState,
      getExportPathDraft,
    });
    return {
      quality: payload.quality,
      aspect_ratio: payload.aspect_ratio,
    };
  }

  function readExportSettingsPayload() {
    const payload = readSharedExportPayload({
      $,
      getState: currentState,
      getExportPathDraft,
    });
    return {
      output_path: payload.output_path,
      target_width: payload.target_width,
      target_height: payload.target_height,
      frame_rate: payload.frame_rate,
      video_codec: payload.video_codec,
      video_bitrate_mbps: payload.video_bitrate_mbps,
      audio_codec: payload.audio_codec,
      audio_sample_rate: payload.audio_sample_rate,
      audio_bitrate_kbps: payload.audio_bitrate_kbps,
      color_space: payload.color_space,
      two_pass: payload.two_pass,
      ffmpeg_preset: payload.ffmpeg_preset,
    };
  }

  function scheduleExportLayoutApply() {
    const payload = readExportLayoutPayload();
    applyExportDraft(payload);
    autoApplyExportLayout(payload);
  }

  function scheduleExportSettingsApply() {
    const payload = readExportSettingsPayload();
    applyExportDraft(payload);
    autoApplyExportSettings(payload);
  }

  return Object.freeze({
    renderExportPresetOptions,
    renderExportLog,
    openExportLogModal,
    closeExportLogModal,
    downloadExportLog,
    syncExportPathControl,
    readExportLayoutPayload,
    readExportSettingsPayload,
    scheduleExportLayoutApply,
    scheduleExportSettingsApply,
  });
}
