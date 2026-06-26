export function createExportPane({
  $ = (id) => document.getElementById(id),
  getState = () => null,
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
      if (description) description.textContent = preset ? preset.description : "Manual custom export settings.";
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
      output.textContent = visibleLines.join("\n");
      if (getActiveProcessingPath() === "/api/export") output.scrollTop = output.scrollHeight;
    }
    if (summary) {
      summary.textContent = getActiveProcessingPath() === "/api/export"
        ? `Export in progress • ${Math.round(getProcessingProgressPercent())}%`
        : "";
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
          : "";
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
      setStatus("");
      return;
    }
    downloadTextFile(`${metricsFileStem()}-export-log.txt`, `${visibleLines.join("\n")}\n`, "text/plain");
    setStatus("Downloaded export log.");
  }

  function syncExportPathControl() {
    return "";
  }

  function readExportLayoutPayload() {
    return {
      quality: $("quality").value,
      aspect_ratio: $("aspect-ratio").value,
    };
  }

  function readExportSettingsPayload() {
    return {
      target_width: $("target-width").value ? Number($("target-width").value) : "",
      target_height: $("target-height").value ? Number($("target-height").value) : "",
      frame_rate: $("frame-rate").value,
      video_codec: $("video-codec").value,
      video_bitrate_mbps: Number($("video-bitrate").value || 15),
      audio_codec: $("audio-codec").value,
      audio_sample_rate: Number($("audio-sample-rate").value || 48000),
      audio_bitrate_kbps: Number($("audio-bitrate").value || 320),
      color_space: $("color-space").value,
      two_pass: $("two-pass").checked,
      multi_track: $("multi-track")?.checked ?? false,
      ffmpeg_preset: $("ffmpeg-preset").value,
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
