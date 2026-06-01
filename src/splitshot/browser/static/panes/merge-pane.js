import { readSharedExportPayload } from "./export-pane.js";

export function createMergePane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  getMergeSourceExpansion = () => new Map(),
  getMergeDraft = () => ({}),
  getPendingMergeSourcePayloads = () => new Map(),
  getMergeSourceCommitTimers = () => new Map(),
  normalizedCoordinateValue = (value) => value,
  clampNumber = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value)),
  opacityPercentValue = (value) => Math.round(Number(value || 0) * 100),
  opacityValueFromPercent = (value) => clampNumber(Number(value || 0), 0, 100) / 100,
  syncControlValue = () => {},
  preserveElementViewportAnchor = (_locator, callback) => callback(),
  withPreservedScrollState = (_elements, callback) => callback(),
  scheduleInteractionPreviewRender = () => {},
  scheduleSecondaryPreviewSync = () => {},
  renderLiveOverlay = () => {},
  renderVideo = () => {},
  callApi = async () => null,
  activity = () => {},
  autoApplyMerge = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  fileName = (value) => String(value || ""),
  buildMediaUrl = (value) => value,
  previewFrameGeometry = () => null,
  pipDefaultsSectionId = "pip-defaults",
  sendKeepaliveJson = () => false,
} = {}) {
  const mergeSourceTrimDrafts = new Map();
  const mergeSourceTrimStatus = new Map();
  const trimmingMergeSources = new Set();

  function currentState() {
    return getState() || {};
  }

  function currentMergeSourceExpansion() {
    return getMergeSourceExpansion() || new Map();
  }

  function currentMergeDraft() {
    const draft = getMergeDraft();
    return draft && typeof draft === "object" ? draft : {};
  }

  function currentPendingMergeSourcePayloads() {
    return getPendingMergeSourcePayloads() || new Map();
  }

  function currentMergeSourceCommitTimers() {
    return getMergeSourceCommitTimers() || new Map();
  }

  function clearStaleMergeSourceTrimState(validSourceIds = new Set()) {
    [...mergeSourceTrimDrafts.keys()].forEach((sourceId) => {
      if (!validSourceIds.has(sourceId)) mergeSourceTrimDrafts.delete(sourceId);
    });
    [...mergeSourceTrimStatus.keys()].forEach((sourceId) => {
      if (!validSourceIds.has(sourceId)) mergeSourceTrimStatus.delete(sourceId);
    });
    [...trimmingMergeSources].forEach((sourceId) => {
      if (!validSourceIds.has(sourceId)) trimmingMergeSources.delete(sourceId);
    });
  }

  function mergeSourceTrimDraft(sourceId) {
    if (!mergeSourceTrimDrafts.has(sourceId)) {
      mergeSourceTrimDrafts.set(sourceId, { start_seconds: "0.000", end_seconds: "" });
    }
    return mergeSourceTrimDrafts.get(sourceId);
  }

  function updateMergeSourceTrimDraft(sourceId, updates = {}) {
    const nextDraft = { ...mergeSourceTrimDraft(sourceId), ...updates };
    mergeSourceTrimDrafts.set(sourceId, nextDraft);
    return nextDraft;
  }

  function setMergeSourceTrimStatus(sourceId, message = "", tone = "hint") {
    if (!sourceId) return;
    if (!message) {
      mergeSourceTrimStatus.delete(sourceId);
      return;
    }
    mergeSourceTrimStatus.set(sourceId, { message: String(message), tone });
  }

  function currentMergeSourceTrimStatus(sourceId) {
    return mergeSourceTrimStatus.get(sourceId) || null;
  }

  function normalizedTrimSecondsInputValue(value, { allowEmpty = false, fallback = "" } = {}) {
    const rawValue = String(value ?? "").trim();
    if (!rawValue) return allowEmpty ? "" : fallback;
    const numericValue = Number(rawValue);
    if (!Number.isFinite(numericValue)) return allowEmpty ? "" : fallback;
    return Math.max(0, numericValue).toFixed(3);
  }

  function trimSecondsToMs(value, { allowEmpty = false } = {}) {
    const rawValue = String(value ?? "").trim();
    if (!rawValue) return allowEmpty ? null : Number.NaN;
    const numericValue = Number(rawValue);
    if (!Number.isFinite(numericValue)) return Number.NaN;
    return Math.max(0, Math.round(numericValue * 1000));
  }

  function currentMergeSourceTrimCaptureValue(source = null) {
    const primaryVideo = $("primary-video");
    const previewSeconds = mergePreviewTargetTime(Number(primaryVideo?.currentTime || 0), source);
    const durationSeconds = Number(source?.asset?.duration_ms || 0) > 0
      ? Number(source.asset.duration_ms) / 1000
      : null;
    const boundedSeconds = durationSeconds === null
      ? previewSeconds
      : Math.min(Math.max(0, previewSeconds), durationSeconds);
    return boundedSeconds.toFixed(3);
  }

  function mergeSourceTrimHint(source = null) {
    if (source?.asset?.is_still_image) {
      return "Still images do not support trim derivatives.";
    }
    if (!String(currentState()?.project?.path || "").trim()) {
      return "Save or create a project folder before trimming added media.";
    }
    const trimDerivative = source?.trim_derivative || {};
    const derivativePath = String(trimDerivative.derivative_path || "").trim();
    const activePathKind = String(trimDerivative.active_path_kind || "").trim().toLowerCase();
    if (activePathKind === "local_derivative" && derivativePath) {
      return `Using local trim derivative ${fileName(derivativePath)}. Re-trim overwrites that local copy and leaves the original source untouched.`;
    }
    if (derivativePath) {
      return `Local trim derivative ${fileName(derivativePath)} is available. Re-trim overwrites that local copy and leaves the original source untouched.`;
    }
    return "Trim creates a local derivative in the project Input folder and leaves the original source untouched.";
  }

  function openMergeTrimSettingsEditor() {
    const button = documentObject.querySelector('[data-tool-pane="merge"] [data-output-hook="run-window"]');
    if (button instanceof HTMLElement) {
      button.click();
      return true;
    }
    return false;
  }

  async function trimMergeSource(sourceId) {
    const source = mergeSourceById(sourceId);
    if (!source) return;
    if (source.asset?.is_still_image) {
      setMergeSourceTrimStatus(sourceId, "Still images do not support trim derivatives.", "error");
      renderMergeMediaList();
      return;
    }
    if (!String(currentState()?.project?.path || "").trim()) {
      setMergeSourceTrimStatus(sourceId, "Save or create a project folder before trimming added media.", "error");
      renderMergeMediaList();
      return;
    }
    const draft = mergeSourceTrimDraft(sourceId);
    const startMs = trimSecondsToMs(draft.start_seconds);
    if (!Number.isFinite(startMs)) {
      setMergeSourceTrimStatus(sourceId, "Enter a valid trim start time in seconds.", "error");
      renderMergeMediaList();
      return;
    }
    const endMs = trimSecondsToMs(draft.end_seconds, { allowEmpty: true });
    if (Number.isNaN(endMs)) {
      setMergeSourceTrimStatus(sourceId, "Enter a valid trim end time in seconds or leave it blank.", "error");
      renderMergeMediaList();
      return;
    }
    if (endMs !== null && endMs <= startMs) {
      setMergeSourceTrimStatus(sourceId, "Trim end must be greater than trim start.", "error");
      renderMergeMediaList();
      return;
    }

    trimmingMergeSources.add(sourceId);
    setMergeSourceTrimStatus(sourceId, "Updating local trim derivative...", "working");
    renderMergeMediaList();

    try {
      const response = await callApi("/api/merge/source/trim", {
        source_id: sourceId,
        trim: {
          start_ms: startMs,
          ...(endMs !== null ? { end_ms: endMs } : {}),
        },
        export: readSharedExportPayload({
          $,
          getState: currentState,
        }),
      });
      if (response) {
        setMergeSourceTrimStatus(sourceId, "Local trim derivative updated.", "success");
      } else {
        setMergeSourceTrimStatus(sourceId, "Trim failed. Review the status bar and try again.", "error");
      }
    } catch (error) {
      setMergeSourceTrimStatus(
        sourceId,
        error?.message || "Trim failed. Review the status bar and try again.",
        "error",
      );
    } finally {
      trimmingMergeSources.delete(sourceId);
      renderMergeMediaList();
    }
  }

  function normalizeMergeDraftValue(key, value) {
    if (!["enabled", "layout", "pip_size_percent", "pip_x", "pip_y"].includes(key)) {
      return undefined;
    }
    if (key === "enabled") return Boolean(value);
    if (key === "layout") return String(value || "side_by_side");
    if (key === "pip_size_percent") {
      return clampNumber(Number(value) || 35, 1, 95);
    }
    return normalizedCoordinateValue(value) ?? 1;
  }

  function applyMergeDraft(payload = {}) {
    const mergeState = currentState()?.project?.merge;
    Object.entries(payload).forEach(([key, value]) => {
      const normalized = normalizeMergeDraftValue(key, value);
      if (normalized === undefined) return;
      currentMergeDraft()[key] = normalized;
      if (mergeState) mergeState[key] = normalized;
    });
  }

  function mergeMergeDraft(project) {
    const mergeState = project?.merge;
    if (!mergeState) return;
    Object.entries(currentMergeDraft()).forEach(([key, value]) => {
      const savedValue = normalizeMergeDraftValue(key, mergeState[key]);
      if (Object.is(value, savedValue)) {
        delete currentMergeDraft()[key];
      } else {
        mergeState[key] = value;
      }
    });
  }

  const mergeSourcePlacementModes = new Set([
    "auto",
    "base",
    "side_by_side",
    "above_below",
    "pip",
    "full_screen_portrait",
    "dual_center_hud",
    "dual_top_hud",
  ]);
  const mergeSourcePlacementSlots = new Set([
    "auto",
    "left",
    "right",
    "top",
    "bottom",
    "center",
    "overlay",
  ]);
  const mergeSourcePlacementTargetKinds = new Set(["primary_video", "merge_source"]);
  const mergeSourcePlacementModeOptions = [
    { value: "auto", label: "Auto (default / fallback)" },
    { value: "base", label: "Base item" },
    { value: "side_by_side", label: "Side by side" },
    { value: "above_below", label: "Above / below" },
    { value: "pip", label: "PiP overlay" },
    { value: "full_screen_portrait", label: "Full-screen portrait" },
    { value: "dual_center_hud", label: "Dual center HUD" },
    { value: "dual_top_hud", label: "Dual top HUD" },
  ];
  const mergeSourcePlacementSlotLabels = {
    auto: "Auto",
    left: "Left",
    right: "Right",
    top: "Top",
    bottom: "Bottom",
    center: "Center",
    overlay: "Overlay",
  };

  function currentSourcePlacement(source = null) {
    const placement = source?.placement;
    return placement && typeof placement === "object" ? placement : {};
  }

  function currentMergeSourceSeedDefaults() {
    const mergeState = currentState()?.project?.merge || {};
    const normalizedLayout = String(mergeState.layout ?? "").trim().toLowerCase();
    const pipSizePercent = Number(mergeState.pip_size_percent);
    const legacyPipSizePercent = Number(String(mergeState.pip_size ?? "").replace(/%$/, ""));
    return {
      placement_mode: mergeSourcePlacementModes.has(normalizedLayout) && normalizedLayout !== "auto"
        ? normalizedLayout
        : "side_by_side",
      pip_size_percent: normalizedPipSizePercentValue(
        Number.isFinite(pipSizePercent) && pipSizePercent > 0 ? pipSizePercent : legacyPipSizePercent,
      ),
      pip_x: normalizedCoordinateValue(mergeState.pip_x) ?? 1,
      pip_y: normalizedCoordinateValue(mergeState.pip_y) ?? 1,
    };
  }

  function currentMergePlacementDefaultMode() {
    return "side_by_side";
  }

  function resolvedPlacementModeValue(value, source = null) {
    const normalized = normalizedPlacementModeValue(value, source);
    return normalized === "auto" ? currentMergePlacementDefaultMode() : normalized;
  }

  function mergeSourcePlacementModeLabel(value = "auto", source = null) {
    const resolvedMode = value === "auto" ? currentMergePlacementDefaultMode() : resolvedPlacementModeValue(value, source);
    return mergeSourcePlacementModeOptions.find((item) => item.value === resolvedMode)?.label || "Side by side";
  }

  function mergeSourcePlacementSlotValuesForMode(mode = "auto", source = null) {
    const resolvedMode = resolvedPlacementModeValue(mode, source);
    if (["side_by_side", "dual_center_hud", "dual_top_hud"].includes(resolvedMode)) {
      return ["left", "right"];
    }
    if (resolvedMode === "above_below") return ["top", "bottom"];
    if (resolvedMode === "pip") return ["overlay", "left", "right", "top", "bottom", "center"];
    return ["center"];
  }

  function mergeSourcePlacementSlotLabel(value = "auto") {
    return mergeSourcePlacementSlotLabels[String(value || "auto").trim().toLowerCase()] || "Auto";
  }

  function mergeSourceItemLabel(source = null) {
    const mergeSources = currentState()?.project?.merge_sources || [];
    const sourceId = sourceIdentifier(source, "");
    const sourceIndex = mergeSources.findIndex(
      (item, index) => sourceIdentifier(item, String(index)) === sourceId,
    );
    const asset = source?.asset || source || {};
    const title = fileName(asset.path || "") || "Added media item";
    return sourceIndex >= 0 ? `${sourceIndex + 1}. ${title}` : title;
  }

  function mergeSourcePlacementTargetSourceOptions(source = null) {
    const currentSourceId = sourceIdentifier(source, "");
    return (currentState()?.project?.merge_sources || [])
      .map((item, index) => ({
        value: sourceIdentifier(item, String(index)),
        label: mergeSourceItemLabel(item),
      }))
      .filter((option) => option.value && option.value !== currentSourceId);
  }

  function resolvedPlacementTargetSourceIdValue(value, source = null) {
    const normalized = normalizedPlacementTargetSourceIdValue(value);
    if (!normalized) return null;
    return mergeSourcePlacementTargetSourceOptions(source).some((option) => option.value === normalized)
      ? normalized
      : null;
  }

  function mergeSourcePlacementSupportsTargetSelection(mode = "auto", source = null) {
    return ["pip", "full_screen_portrait"].includes(resolvedPlacementModeValue(mode, source));
  }

  function currentSourcePlacementTargetLabel(source = null, placement = null) {
    const placementValue = currentSourcePlacementValue(source, placement);
    if (placementValue.target_kind !== "merge_source") return "Primary video";
    const targetSourceId = resolvedPlacementTargetSourceIdValue(placementValue.target_source_id, source);
    const targetSource = targetSourceId ? mergeSourceById(targetSourceId) : null;
    return targetSource ? mergeSourceItemLabel(targetSource) : "Primary video";
  }

  function placementSlotControlValue(value, mode = "auto", source = null) {
    const normalized = String(value ?? "").trim().toLowerCase();
    if (!normalized || normalized === "auto") return "auto";
    return mergeSourcePlacementSlotValuesForMode(mode, source).includes(normalized) ? normalized : "auto";
  }

  function previewAutoPlacementSlotValue(mode = "auto", source = null) {
    const resolvedMode = resolvedPlacementModeValue(mode, source);
    if (resolvedMode === "above_below") return "bottom";
    if (["side_by_side", "dual_center_hud", "dual_top_hud"].includes(resolvedMode)) return "right";
    if (resolvedMode === "pip") return "overlay";
    return "center";
  }

  function resolvedPreviewPlacementSlotValue(value, { mode = "auto", source = null } = {}) {
    const controlValue = placementSlotControlValue(value, mode, source);
    return controlValue === "auto" ? previewAutoPlacementSlotValue(mode, source) : controlValue;
  }

  function currentSourcePlacementValue(source = null, placement = null) {
    return normalizedPlacementPayload(placement ?? source?.placement, source);
  }

  function currentSourcePlacementPreviewMode(source = null, placement = null) {
    return resolvedPlacementModeValue(currentSourcePlacementValue(source, placement).mode, source);
  }

  function currentSourcePlacementPreviewSlot(source = null, placement = null) {
    const placementValue = currentSourcePlacementValue(source, placement);
    return resolvedPreviewPlacementSlotValue(placementValue.slot, { mode: placementValue.mode, source });
  }

  function mergeSourcePlacementUsesPreviewDrag(source = null, placement = null) {
    return currentSourcePlacementPreviewMode(source, placement) === "pip"
      && currentSourcePlacementPreviewSlot(source, placement) === "overlay";
  }

  function cameraRolePriorityValue(role = "") {
    return {
      primary: 0,
      static: 1,
      follow: 2,
      detail: 3,
    }[normalizedAngleRoleValue(role)] ?? 4;
  }

  function mergeSourceSeedPlacementModeForRole(angleRole, source = null) {
    const normalizedRole = normalizedAngleRoleValue(angleRole, source);
    const projectDefaultMode = currentMergeSourceSeedDefaults().placement_mode;
    if (normalizedRole === "primary") return "base";
    if (normalizedRole === "detail") {
      return ["pip", "full_screen_portrait"].includes(projectDefaultMode) ? projectDefaultMode : "pip";
    }
    if (["side_by_side", "above_below", "dual_center_hud", "dual_top_hud"].includes(projectDefaultMode)) {
      return projectDefaultMode;
    }
    return "side_by_side";
  }

  function mergeSourceSeedPlacementSlotForRole(angleRole, mode, source = null) {
    const normalizedRole = normalizedAngleRoleValue(angleRole, source);
    if (["side_by_side", "dual_center_hud", "dual_top_hud"].includes(mode)) {
      return normalizedRole === "static" ? "left" : "right";
    }
    if (mode === "above_below") return normalizedRole === "static" ? "top" : "bottom";
    if (mode === "pip") return "overlay";
    return "center";
  }

  function mergeSourceBaseTargetSortKey(source = null) {
    const mode = currentSourcePlacementPreviewMode(source);
    const sourceId = sourceIdentifier(source, "");
    const mergeSources = currentState()?.project?.merge_sources || [];
    const sourceIndex = Math.max(
      0,
      mergeSources.findIndex((item, index) => sourceIdentifier(item, String(index)) === sourceId),
    );
    const modePriority = ["base", "full_screen_portrait"].includes(mode)
      ? 0
      : ["side_by_side", "above_below", "dual_center_hud", "dual_top_hud"].includes(mode)
        ? 1
        : 2;
    return [modePriority, cameraRolePriorityValue(currentSourceAngleRole(source)), sourceIndex];
  }

  function preferredMergeSourceBaseTarget(source = null) {
    const currentSourceId = sourceIdentifier(source, "");
    const mergeSources = (currentState()?.project?.merge_sources || [])
      .filter((item, index) => {
        const candidateId = sourceIdentifier(item, String(index));
        return candidateId && candidateId !== currentSourceId && item?.asset?.path;
      })
      .sort((left, right) => {
        const leftKey = mergeSourceBaseTargetSortKey(left);
        const rightKey = mergeSourceBaseTargetSortKey(right);
        return leftKey[0] - rightKey[0] || leftKey[1] - rightKey[1] || leftKey[2] - rightKey[2];
      });
    return mergeSources.find((candidate) => {
      const mode = currentSourcePlacementPreviewMode(candidate);
      return ["base", "side_by_side", "above_below", "full_screen_portrait", "dual_center_hud", "dual_top_hud"].includes(mode);
    }) || null;
  }

  function mergeSourceSeedTargetForRole(angleRole, source = null, mode = "side_by_side") {
    if (!["pip", "full_screen_portrait"].includes(mode)) {
      return { target_kind: "primary_video", target_source_id: null };
    }
    const targetSource = preferredMergeSourceBaseTarget(source);
    if (!targetSource) return { target_kind: "primary_video", target_source_id: null };
    return {
      target_kind: "merge_source",
      target_source_id: sourceIdentifier(targetSource, ""),
    };
  }

  function mergeSourceSeedPlacementForRole(angleRole, source = null) {
    const mode = mergeSourceSeedPlacementModeForRole(angleRole, source);
    const slot = mergeSourceSeedPlacementSlotForRole(angleRole, mode, source);
    return {
      mode,
      slot,
      ...mergeSourceSeedTargetForRole(angleRole, source, mode),
    };
  }

  function mergeSourceMatchesRoleSeedDefaults(source = null, referenceRole = null) {
    if (!source) return false;
    const expectedPlacement = mergeSourceSeedPlacementForRole(
      referenceRole ?? currentSourceAngleRole(source),
      source,
    );
    const currentPlacement = currentSourcePlacementValue(source);
    if (currentPlacement.mode !== expectedPlacement.mode) return false;
    if (currentSourcePlacementPreviewSlot(source) !== expectedPlacement.slot) return false;
    const currentTargetSourceId = resolvedPlacementTargetSourceIdValue(currentPlacement.target_source_id, source);
    return currentPlacement.target_kind === expectedPlacement.target_kind
      && currentTargetSourceId === expectedPlacement.target_source_id;
  }

  function syncPlacementSlotControl(control, { mode = "auto", source = null, value = "auto" } = {}) {
    if (!control) return;
    const options = [
      { value: "auto", label: mergeSourcePlacementSlotLabel("auto") },
      ...mergeSourcePlacementSlotValuesForMode(mode, source).map((slotValue) => ({
        value: slotValue,
        label: mergeSourcePlacementSlotLabel(slotValue),
      })),
    ];
    control.innerHTML = "";
    options.forEach(({ value: optionValue, label }) => {
      const option = documentObject.createElement("option");
      option.value = optionValue;
      option.textContent = label;
      control.appendChild(option);
    });
    syncControlValue(control, placementSlotControlValue(value, mode, source));
  }

  function syncPlacementTargetSourceControl(control, { source = null, value = null } = {}) {
    if (!control) return;
    const options = mergeSourcePlacementTargetSourceOptions(source);
    control.innerHTML = "";
    if (options.length === 0) {
      const option = documentObject.createElement("option");
      option.value = "";
      option.textContent = "No other added item available";
      control.appendChild(option);
      control.disabled = true;
      syncControlValue(control, "");
      return;
    }
    control.disabled = false;
    options.forEach(({ value: optionValue, label }) => {
      const option = documentObject.createElement("option");
      option.value = optionValue;
      option.textContent = label;
      control.appendChild(option);
    });
    syncControlValue(control, resolvedPlacementTargetSourceIdValue(value, source) ?? options[0].value);
  }

  function defaultPlacementSlotValue(mode = "auto") {
    if (mode === "pip") return "overlay";
    if (["base", "full_screen_portrait", "dual_center_hud", "dual_top_hud"].includes(mode)) {
      return "center";
    }
    return "auto";
  }

  function normalizedPlacementTargetSourceIdValue(value) {
    const normalized = String(value ?? "").trim();
    return normalized || null;
  }

  function normalizedPlacementModeValue(value, source = null) {
    const currentPlacement = currentSourcePlacement(source);
    const normalized = String(value ?? currentPlacement.mode ?? "").trim().toLowerCase();
    return mergeSourcePlacementModes.has(normalized) ? normalized : "auto";
  }

  function normalizedPlacementSlotValue(value, { mode = "auto", source = null } = {}) {
    const normalizedMode = normalizedPlacementModeValue(mode, source);
    const currentPlacement = currentSourcePlacement(source);
    const normalized = String(value ?? currentPlacement.slot ?? "").trim().toLowerCase();
    return mergeSourcePlacementSlots.has(normalized)
      ? normalized
      : defaultPlacementSlotValue(normalizedMode);
  }

  function normalizedPlacementTargetKindValue(value, { targetSourceId = null, source = null } = {}) {
    const currentPlacement = currentSourcePlacement(source);
    const normalizedTargetSourceId = normalizedPlacementTargetSourceIdValue(
      targetSourceId ?? currentPlacement.target_source_id,
    );
    const normalized = String(value ?? currentPlacement.target_kind ?? "").trim().toLowerCase();
    if (normalized === "merge_source") {
      return normalizedTargetSourceId ? "merge_source" : "primary_video";
    }
    if (mergeSourcePlacementTargetKinds.has(normalized)) return normalized;
    return normalizedTargetSourceId ? "merge_source" : "primary_video";
  }

  function normalizedPlacementPayload(value = null, source = null) {
    const placement = value && typeof value === "object" ? value : {};
    const currentPlacement = currentSourcePlacement(source);
    const targetSourceId = resolvedPlacementTargetSourceIdValue(
      placement.target_source_id ?? currentPlacement.target_source_id,
      source,
    );
    const mode = normalizedPlacementModeValue(placement.mode ?? currentPlacement.mode, source);
    const targetKind = normalizedPlacementTargetKindValue(
      placement.target_kind ?? currentPlacement.target_kind,
      { targetSourceId, source },
    );
    return {
      mode,
      slot: normalizedPlacementSlotValue(placement.slot ?? currentPlacement.slot, { mode, source }),
      target_kind: targetKind,
      target_source_id: targetKind === "merge_source" ? targetSourceId : null,
    };
  }

  function mergeSourcePlacementState(source = null, placement = null) {
    return { ...currentSourcePlacement(source), ...normalizedPlacementPayload(placement, source) };
  }

  function mergeSourceDraftValuesEqual(left, right) {
    if (Object.is(left, right)) return true;
    if (left && right && typeof left === "object" && typeof right === "object") {
      return JSON.stringify(left) === JSON.stringify(right);
    }
    return false;
  }

  function readSourcePlacementPayload(root, source = null) {
    const placement = currentSourcePlacement(source);
    const modeControl = root?.querySelector('[data-merge-source-field="placement_mode"]');
    const slotControl = root?.querySelector('[data-merge-source-field="placement_slot"]');
    const targetKindControl = root?.querySelector('[data-merge-source-field="target_kind"]');
    const targetSourceControl = root?.querySelector('[data-merge-source-field="target_source_id"]');
    return normalizedPlacementPayload(
      {
        mode: modeControl?.value ?? placement.mode,
        slot: slotControl?.value ?? placement.slot,
        target_kind: targetKindControl?.value ?? placement.target_kind,
        target_source_id: targetSourceControl?.value ?? placement.target_source_id,
      },
      source,
    );
  }

  function normalizeMergeSourceDraftValue(key, value, source = null) {
    if (!["camera_role", "angle_role", "pip_size_percent", "pip_x", "pip_y", "opacity", "placement"].includes(key)) {
      return undefined;
    }
    if (key === "placement") return normalizedPlacementPayload(value, source);
    if (key === "camera_role" || key === "angle_role") return normalizedAngleRoleValue(value, source);
    if (key === "pip_size_percent") return clampNumber(Number(value) || 35, 1, 95);
    if (key === "opacity") return currentSourceOpacity({ opacity: value });
    return normalizedCoordinateValue(value) ?? 1;
  }

  function mergePendingMergeSourcePayloads(project) {
    const mergeSources = Array.isArray(project?.merge_sources) ? project.merge_sources : [];
    if (mergeSources.length === 0 || currentPendingMergeSourcePayloads().size === 0) return;
    currentPendingMergeSourcePayloads().forEach((payload, sourceId) => {
      const source = mergeSources.find((item, index) => sourceIdentifier(item, String(index)) === sourceId);
      if (!source) {
        currentPendingMergeSourcePayloads().delete(sourceId);
        return;
      }
      const draftEntries = Object.entries(payload || {})
        .filter(([key]) => key !== "source_id")
        .map(([key, value]) => {
          const draftValue = normalizeMergeSourceDraftValue(key, value, source);
          const savedValue = normalizeMergeSourceDraftValue(
            key,
            key === "camera_role" || key === "angle_role"
              ? (source.camera_role ?? source.angle_role)
              : source[key],
            source,
          );
          return [key, draftValue, savedValue];
        })
        .filter((entry) => entry[1] !== undefined);
      if (draftEntries.length === 0) {
        currentPendingMergeSourcePayloads().delete(sourceId);
        return;
      }
      const isCommitted = draftEntries.every(([, draftValue, savedValue]) => mergeSourceDraftValuesEqual(draftValue, savedValue));
      if (isCommitted) {
        currentPendingMergeSourcePayloads().delete(sourceId);
        return;
      }
      draftEntries.forEach(([key, draftValue]) => {
        if (key === "placement") {
          source.placement = mergeSourcePlacementState(source, draftValue);
          return;
        }
        if (key === "camera_role" || key === "angle_role") {
          source.camera_role = draftValue;
          delete source.angle_role;
          return;
        }
        source[key] = draftValue;
      });
    });
  }

  function normalizedPipSizePercentValue(value, fallback = 35) {
    const numericValue = Number(value);
    if (Number.isFinite(numericValue) && numericValue > 0) {
      return clampNumber(numericValue, 1, 95);
    }
    const numericFallback = Number(fallback);
    return clampNumber(Number.isFinite(numericFallback) && numericFallback > 0 ? numericFallback : 35, 1, 95);
  }

  function currentPipSizePercent(source = null, fallback = 35) {
    return normalizedPipSizePercentValue(source?.pip_size_percent, fallback);
  }

  function currentSourcePipCoordinate(source = null, axis = "x", fallback = 1) {
    const key = axis === "y" ? "pip_y" : "pip_x";
    return normalizedCoordinateValue(source?.[key]) ?? fallback;
  }

    function sourceIdentifier(source, fallback = "") {
      const asset = source?.asset || source || {};
      return source?.id || asset.id || fallback || fileName(asset.path || "");
    }

    function currentSourceSyncOffsetMs(source = null) {
      return Math.round(Number(source?.sync_offset_ms) || 0);
    }

    function currentSourceOpacity(source = null) {
      return clampNumber(Number(source?.opacity ?? 1) || 0, 0, 1);
    }

    const mergeSourceAngleRoles = [
      { value: "primary", label: "Primary" },
      { value: "follow", label: "Follow" },
      { value: "static", label: "Static" },
      { value: "detail", label: "Detail" },
    ];

    function normalizedAngleRoleValue(value, source = null) {
      const normalized = String(value || "").trim().toLowerCase();
      if (mergeSourceAngleRoles.some((item) => item.value === normalized)) return normalized;
      return source?.asset?.is_still_image ? "detail" : "follow";
    }

    function currentSourceAngleRole(source = null) {
      return normalizedAngleRoleValue(source?.camera_role ?? source?.angle_role, source);
    }

    function formatSyncOffsetLabel(offsetMs) {
      const numeric = Math.round(Number(offsetMs) || 0);
      return `Sync ${numeric > 0 ? "+" : ""}${numeric} ms`;
    }

    function sourceSyncStatusLabel(source = null) {
      if (!source?.supports_sync_analysis) return "";
      const status = String(source.sync_analysis_status || "idle");
      if (status === "running") return "Analyzing beep sync...";
      if (status === "ready") {
        const beepMs = Number(source.secondary_beep_time_ms);
        const sourceLabel = String(source.sync_offset_source || "manual");
        return Number.isFinite(beepMs)
          ? `Beep ${Math.round(beepMs)} ms • ${sourceLabel === "auto" ? "ShotML sync applied" : "manual sync active"}`
          : "Beep detected.";
      }
      if (status === "no_beep") return "No beep detected. Manual sync is still available.";
      return String(source.sync_analysis_message || "");
    }

    function mergePreviewTargetTime(primaryTime, source = null) {
      return Math.max(0, primaryTime + (currentSourceSyncOffsetMs(source) / 1000));
    }

    function mergeSourceById(sourceId) {
      return (currentState()?.project?.merge_sources || []).find((source, index) => sourceIdentifier(source, String(index)) === sourceId) || null;
    }

    function isMergeSourceExpanded(sourceId) {
      if (!sourceId) return false;
      if (currentMergeSourceExpansion().has(sourceId)) return Boolean(currentMergeSourceExpansion().get(sourceId));
      if (sourceId === pipDefaultsSectionId) return true;
      const firstSource = currentState()?.project?.merge_sources?.[0] || null;
      if (firstSource && sourceId === sourceIdentifier(firstSource, "0")) return true;
      return false;
    }

    function setMergeSourceExpanded(sourceId, expanded) {
      if (!sourceId) return;
      currentMergeSourceExpansion().set(sourceId, Boolean(expanded));
      syncLocalProjectUiState();
      scheduleProjectUiStateApply();
    }

    function syncMergeSourceControls(sourceId, pipX, pipY, pipSizePercent = null, syncOffsetMs = null, opacity = null, angleRole = null, placement = null) {
        const source = mergeSourceById(sourceId);
      const xValue = Number.isFinite(pipX) ? pipX.toFixed(3) : "";
      const yValue = Number.isFinite(pipY) ? pipY.toFixed(3) : "";
      const sizeValue = Number.isFinite(pipSizePercent) ? Math.round(pipSizePercent) : "";
      const offsetValue = Math.round(Number(syncOffsetMs) || 0);
      const opacityValue = String(opacityPercentValue(opacity ?? 1));
        const roleValue = normalizedAngleRoleValue(angleRole, source);
        const placementValue = currentSourcePlacementValue(source, placement);
      const targetOptions = mergeSourcePlacementTargetSourceOptions(source);
      const supportsTargetSelection = mergeSourcePlacementSupportsTargetSelection(placementValue.mode, source);
      const usesPreviewDrag = mergeSourcePlacementUsesPreviewDrag(source, placementValue);
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="x"]`).forEach((input) => {
        syncControlValue(input, xValue);
        const field = input.closest(".merge-source-field");
        if (field) field.hidden = !usesPreviewDrag;
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="y"]`).forEach((input) => {
        syncControlValue(input, yValue);
        const field = input.closest(".merge-source-field");
        if (field) field.hidden = !usesPreviewDrag;
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="size"]`).forEach((input) => {
        syncControlValue(input, sizeValue);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-output="size"]`).forEach((output) => {
        output.textContent = sizeValue === "" ? "" : `${sizeValue}%`;
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="opacity"]`).forEach((input) => {
        syncControlValue(input, opacityValue);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="camera_role"]`).forEach((input) => {
        syncControlValue(input, roleValue);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="placement_mode"]`).forEach((input) => {
        syncControlValue(input, placementValue.mode);
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="placement_slot"]`).forEach((input) => {
        syncPlacementSlotControl(input, { mode: placementValue.mode, source, value: placementValue.slot });
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="target_kind"]`).forEach((input) => {
        syncControlValue(input, placementValue.target_kind);
        const mergeSourceOption = input.querySelector('option[value="merge_source"]');
        if (mergeSourceOption) mergeSourceOption.disabled = targetOptions.length === 0;
        const field = input.closest(".merge-source-field");
        if (field) field.hidden = !supportsTargetSelection;
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="target_source_id"]`).forEach((input) => {
        syncPlacementTargetSourceControl(input, { source, value: placementValue.target_source_id });
        const field = input.closest(".merge-source-field");
        if (field) field.hidden = !supportsTargetSelection || placementValue.target_kind !== "merge_source";
      });
      documentObject.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-sync-label]`).forEach((label) => {
        label.textContent = formatSyncOffsetLabel(offsetValue);
      });
    }

    function updateLocalMergeSourcePosition(
      sourceId,
      pipX,
      pipY,
      pipSizePercent = null,
      opacity = null,
      angleRole = null,
      placement = null,
      { reseedRolePlacement = false } = {},
    ) {
      const source = mergeSourceById(sourceId);
      if (!source || !currentState()?.project) return;
      const nextSize = normalizedPipSizePercentValue(pipSizePercent ?? source.pip_size_percent);
      const nextX = normalizedCoordinateValue(pipX) ?? 1;
      const nextY = normalizedCoordinateValue(pipY) ?? 1;
      const nextOpacity = currentSourceOpacity({ opacity: opacity ?? source.opacity ?? 1 });
      const nextAngleRole = normalizedAngleRoleValue(
        angleRole ?? source.camera_role ?? source.angle_role,
        source,
      );
      let nextPlacement = mergeSourcePlacementState(source, placement);
      if (
        reseedRolePlacement
        && nextAngleRole !== currentSourceAngleRole(source)
        && mergeSourceMatchesRoleSeedDefaults(source, currentSourceAngleRole(source))
      ) {
        nextPlacement = mergeSourcePlacementState(source, mergeSourceSeedPlacementForRole(nextAngleRole, source));
      }
      source.pip_size_percent = nextSize;
      source.pip_x = nextX;
      source.pip_y = nextY;
      source.opacity = nextOpacity;
      source.camera_role = nextAngleRole;
      delete source.angle_role;
      source.placement = nextPlacement;
      syncMergeSourceControls(sourceId, nextX, nextY, nextSize, source.sync_offset_ms, nextOpacity, nextAngleRole, nextPlacement);
    }

    function updateLocalMergeSourceSyncOffset(sourceId, syncOffsetMs) {
      const source = mergeSourceById(sourceId);
      if (!source || !currentState()?.project) return;
      source.sync_offset_ms = Math.round(Number(syncOffsetMs) || 0);
      if (currentState().project.merge_sources?.[0]?.id === sourceId) {
        currentState().project.analysis.sync_offset_ms = source.sync_offset_ms;
      }
      syncMergeSourceControls(
        sourceId,
        normalizedCoordinateValue(source.pip_x),
        normalizedCoordinateValue(source.pip_y),
        currentPipSizePercent(source),
        source.sync_offset_ms,
        currentSourceOpacity(source),
        currentSourceAngleRole(source),
        source.placement,
      );
    }

    function mergeSourcePositionPayload(sourceId, source) {
      return {
        source_id: sourceId,
        camera_role: currentSourceAngleRole(source),
        pip_size_percent: currentPipSizePercent(source),
        pip_x: normalizedCoordinateValue(source?.pip_x) ?? 1,
        pip_y: normalizedCoordinateValue(source?.pip_y) ?? 1,
        opacity: currentSourceOpacity(source),
        placement: normalizedPlacementPayload(source?.placement, source),
      };
    }

    function hydratedMergeSourcePlacement(source = null, seedDefaults = currentMergeSourceSeedDefaults()) {
      const currentPlacement = normalizedPlacementPayload(source?.placement, source);
      const mode = currentPlacement.mode === "auto" ? seedDefaults.placement_mode : currentPlacement.mode;
      const targetSourceId = resolvedPlacementTargetSourceIdValue(currentPlacement.target_source_id, source);
      const targetKind = normalizedPlacementTargetKindValue(currentPlacement.target_kind, {
        targetSourceId,
        source,
      });
      return {
        mode,
        slot: normalizedPlacementSlotValue(currentPlacement.slot, { mode, source }),
        target_kind: targetKind,
        target_source_id: targetKind === "merge_source" ? targetSourceId : null,
      };
    }

    function hydrateMergeSourceCompositionTruth(
      source = null,
      fallbackSourceId = "",
      seedDefaults = currentMergeSourceSeedDefaults(),
    ) {
      if (!source || typeof source !== "object") return null;
      const nextPipSize = currentPipSizePercent(source, seedDefaults.pip_size_percent);
      const nextPipX = currentSourcePipCoordinate(source, "x", seedDefaults.pip_x);
      const nextPipY = currentSourcePipCoordinate(source, "y", seedDefaults.pip_y);
      const nextPlacement = hydratedMergeSourcePlacement(source, seedDefaults);
      let changed = false;
      if (!mergeSourceDraftValuesEqual(source.pip_size_percent, nextPipSize)) {
        source.pip_size_percent = nextPipSize;
        changed = true;
      }
      if (!mergeSourceDraftValuesEqual(source.pip_x, nextPipX)) {
        source.pip_x = nextPipX;
        changed = true;
      }
      if (!mergeSourceDraftValuesEqual(source.pip_y, nextPipY)) {
        source.pip_y = nextPipY;
        changed = true;
      }
      if (
        !mergeSourceDraftValuesEqual(normalizedPlacementPayload(source.placement, source), nextPlacement)
        || !mergeSourceDraftValuesEqual(source.placement, nextPlacement)
      ) {
        source.placement = nextPlacement;
        changed = true;
      }
      return changed ? mergeSourcePositionPayload(sourceIdentifier(source, fallbackSourceId), source) : null;
    }

    function hydrateMergeSourcesFromDefaults({ persist = true } = {}) {
      const mergeSources = currentState()?.project?.merge_sources || [];
      const seedDefaults = currentMergeSourceSeedDefaults();
      const hydrationPayloads = mergeSources
        .map((source, index) => hydrateMergeSourceCompositionTruth(source, String(index), seedDefaults))
        .filter(Boolean);
      if (persist) hydrationPayloads.forEach((payload) => scheduleMergeSourceCommit(payload));
      return hydrationPayloads;
    }

    function syncMergePreviewStateFromControls() {
      if (!currentState()?.project) return;
      const merge = currentState().project.merge;
      merge.enabled = $("merge-enabled").checked;
      merge.layout = $("merge-layout").value;
      merge.pip_size_percent = clampNumber(Number($("pip-size").value) || 35, 1, 95);
      merge.pip_x = normalizedCoordinateValue($("pip-x").value) ?? 1;
      merge.pip_y = normalizedCoordinateValue($("pip-y").value) ?? 1;
    }

  function mergeSourcePipRect(source, frameRect, pipSizeValue = null) {
    const asset = source.asset || source;
    const sourceWidth = Math.max(1, asset.width || 1);
    const sourceHeight = Math.max(1, asset.height || 1);
    const effectivePipSize = currentPipSizePercent(source, pipSizeValue ?? 35);
    let insetWidth = Math.max(1, Math.round(frameRect.width * (effectivePipSize / 100)));
    let insetHeight = Math.max(1, Math.round((sourceHeight / sourceWidth) * insetWidth));
    if (insetHeight > frameRect.height) {
      const fitScale = frameRect.height / insetHeight;
      insetWidth = Math.max(1, Math.round(insetWidth * fitScale));
      insetHeight = Math.max(1, Math.round(insetHeight * fitScale));
    }
    const travelX = Math.max(0, frameRect.width - insetWidth);
    const travelY = Math.max(0, frameRect.height - insetHeight);
    const pipX = currentSourcePipCoordinate(source, "x", 1);
    const pipY = currentSourcePipCoordinate(source, "y", 1);
    return {
      left: frameRect.left + (travelX * pipX),
      top: frameRect.top + (travelY * pipY),
      width: insetWidth,
      height: insetHeight,
    };
  }

  function mergePreviewFrameRect(video, stage) {
    const previewRect = previewFrameGeometry(video, stage)?.frameRect;
    if (
      previewRect
      && Number.isFinite(previewRect.left)
      && Number.isFinite(previewRect.top)
      && Number.isFinite(previewRect.width)
      && Number.isFinite(previewRect.height)
      && previewRect.width > 0
      && previewRect.height > 0
    ) {
      return previewRect;
    }
    const fallbackWidth = Math.max(1, stage?.clientWidth || video?.clientWidth || 0);
    const fallbackHeight = Math.max(1, stage?.clientHeight || video?.clientHeight || 0);
    if (fallbackWidth <= 0 || fallbackHeight <= 0) return null;
    return {
      left: 0,
      top: 0,
      width: fallbackWidth,
      height: fallbackHeight,
    };
  }

  function mergeSourcePipPreviewRect(source, frameRect, pipSizeValue = null, slot = "overlay") {
    if (slot === "overlay") return mergeSourcePipRect(source, frameRect, pipSizeValue);
    const slotCoordinates = {
      left: { pip_x: 0, pip_y: 0.5 },
      right: { pip_x: 1, pip_y: 0.5 },
      top: { pip_x: 0.5, pip_y: 0 },
      bottom: { pip_x: 0.5, pip_y: 1 },
      center: { pip_x: 0.5, pip_y: 0.5 },
    }[slot] || {
      pip_x: currentSourcePipCoordinate(source, "x", 1),
      pip_y: currentSourcePipCoordinate(source, "y", 1),
    };
    return mergeSourcePipRect({ ...source, ...slotCoordinates }, frameRect, pipSizeValue);
  }

  function mergeSourcePreviewRect(source, frameRect, pipSizeValue = null) {
    const mode = currentSourcePlacementPreviewMode(source);
    const slot = currentSourcePlacementPreviewSlot(source);
    if (mode === "base") {
      return {
        left: frameRect.left,
        top: frameRect.top,
        width: frameRect.width,
        height: frameRect.height,
      };
    }
    if (mode === "side_by_side") {
      const leftWidth = Math.max(1, Math.floor(frameRect.width / 2));
      const rightWidth = Math.max(1, frameRect.width - leftWidth);
      const useLeft = slot === "left";
      return {
        left: useLeft ? frameRect.left : frameRect.left + leftWidth,
        top: frameRect.top,
        width: useLeft ? leftWidth : rightWidth,
        height: frameRect.height,
      };
    }
    if (mode === "above_below") {
      const topHeight = Math.max(1, Math.floor(frameRect.height / 2));
      const bottomHeight = Math.max(1, frameRect.height - topHeight);
      const useTop = slot === "top";
      return {
        left: frameRect.left,
        top: useTop ? frameRect.top : frameRect.top + topHeight,
        width: frameRect.width,
        height: useTop ? topHeight : bottomHeight,
      };
    }
    if (mode === "full_screen_portrait") {
      const portraitWidth = Math.max(1, Math.min(frameRect.width, Math.round(frameRect.height * (9 / 16))));
      return {
        left: frameRect.left + Math.max(0, Math.round((frameRect.width - portraitWidth) / 2)),
        top: frameRect.top,
        width: portraitWidth,
        height: frameRect.height,
      };
    }
    if (mode === "dual_center_hud") {
      const gutterWidth = Math.min(
        Math.max(24, Math.round(frameRect.height * 0.18)),
        Math.max(24, frameRect.width - 2),
      );
      const leftWidth = Math.max(1, Math.floor((frameRect.width - gutterWidth) / 2));
      const rightWidth = Math.max(1, frameRect.width - gutterWidth - leftWidth);
      const useLeft = slot === "left";
      return {
        left: useLeft ? frameRect.left : frameRect.left + leftWidth + gutterWidth,
        top: frameRect.top,
        width: useLeft ? leftWidth : rightWidth,
        height: frameRect.height,
      };
    }
    if (mode === "dual_top_hud") {
      const hudHeight = Math.min(
        Math.max(24, Math.round(frameRect.height * 0.18)),
        Math.max(24, frameRect.height - 2),
      );
      const leftWidth = Math.max(1, Math.floor(frameRect.width / 2));
      const rightWidth = Math.max(1, frameRect.width - leftWidth);
      const useLeft = slot === "left";
      return {
        left: useLeft ? frameRect.left : frameRect.left + leftWidth,
        top: frameRect.top + hudHeight,
        width: useLeft ? leftWidth : rightWidth,
        height: Math.max(1, frameRect.height - hudHeight),
      };
    }
    return mergeSourcePipPreviewRect(source, frameRect, pipSizeValue, slot);
  }

  function mergeSourcePreviewZIndex(source, index = 0) {
    const mode = currentSourcePlacementPreviewMode(source);
    if (mode === "base") return String(10 + index);
    if (["side_by_side", "above_below", "dual_center_hud", "dual_top_hud"].includes(mode)) {
      return String(20 + index);
    }
    if (mode === "full_screen_portrait") return String(30 + index);
    return String(40 + index);
  }

  function ensureMergePreviewItem(layer, source) {
    const asset = source.asset || source;
    const sourceId = sourceIdentifier(source, fileName(asset.path || ""));
    let item = layer.querySelector(`.merge-preview-item[data-source-id="${sourceId}"]`);
    if (!item) {
      item = documentObject.createElement("div");
      item.className = "merge-preview-item";
      item.dataset.sourceId = sourceId;
      layer.appendChild(item);
    }
    item.dataset.sourceId = sourceId;
    item.dataset.mediaType = asset.is_still_image ? "image" : "video";
    let media = item.firstElementChild;
    const desiredTag = asset.is_still_image ? "IMG" : "VIDEO";
    if (!(media instanceof HTMLElement) || media.tagName !== desiredTag) {
      item.innerHTML = "";
      media = documentObject.createElement(asset.is_still_image ? "img" : "video");
      if (media instanceof HTMLVideoElement) {
        media.defaultMuted = false;
        media.muted = false;
        media.volume = 1;
        media.playsInline = true;
        media.disablePictureInPicture = true;
        media.preload = "auto";
        ["loadedmetadata", "loadeddata"].forEach((eventName) => {
          media.addEventListener(eventName, () => {
            scheduleSecondaryPreviewSync();
            renderLiveOverlay();
          });
        });
      }
      item.appendChild(media);
    }
    const mediaPath = buildMediaUrl(`/media/merge/${sourceId}`, asset.path || "");
    if (media instanceof HTMLImageElement) {
      if (media.dataset.sourcePath !== asset.path || media.dataset.mediaUrl !== mediaPath) {
        media.dataset.sourcePath = asset.path;
        media.dataset.mediaUrl = mediaPath;
        media.src = mediaPath;
      }
    } else if (media instanceof HTMLVideoElement && (media.dataset.sourcePath !== asset.path || media.dataset.mediaUrl !== mediaPath)) {
      media.dataset.sourcePath = asset.path;
      media.dataset.mediaUrl = mediaPath;
      media.src = mediaPath;
      media.load();
    }
    if (media instanceof HTMLImageElement) {
      media.style.opacity = String(currentSourceOpacity(source));
    } else if (media instanceof HTMLVideoElement) {
      media.style.opacity = String(currentSourceOpacity(source));
    }
    return item;
  }

  function renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue) {
    const layer = $("merge-preview-layer");
    if (!layer) return;
    if (!($("show-pip")?.checked ?? true)) {
      layer.hidden = true;
      layer.innerHTML = "";
      return;
    }
    const frameRect = mergePreviewFrameRect(video, stage);
    if (!frameRect || mergeSources.length === 0) {
      layer.hidden = true;
      layer.innerHTML = "";
      return;
    }
    layer.hidden = false;
    const previewRects = new Map();
    const resolveSourcePreviewRect = (source, activeStack = new Set()) => {
      const sourceId = sourceIdentifier(source, fileName(source?.asset?.path || ""));
      if (previewRects.has(sourceId)) return previewRects.get(sourceId);
      if (activeStack.has(sourceId)) return frameRect;
      activeStack.add(sourceId);
      const placementValue = currentSourcePlacementValue(source);
      let targetFrameRect = frameRect;
      if (
        mergeSourcePlacementSupportsTargetSelection(placementValue.mode, source)
        && placementValue.target_kind === "merge_source"
      ) {
        const targetSourceId = resolvedPlacementTargetSourceIdValue(placementValue.target_source_id, source);
        const targetSource = targetSourceId
          ? mergeSources.find((item, index) => sourceIdentifier(item, String(index)) === targetSourceId)
          : null;
        if (targetSource) {
          targetFrameRect = resolveSourcePreviewRect(targetSource, activeStack);
        }
      }
      const rect = mergeSourcePreviewRect(source, targetFrameRect, pipSizeValue);
      previewRects.set(sourceId, rect);
      activeStack.delete(sourceId);
      return rect;
    };
    const expectedIds = new Set(mergeSources.map((source, index) => sourceIdentifier(source, String(index))));
    layer.querySelectorAll(".merge-preview-item[data-source-id]").forEach((item) => {
      if (!expectedIds.has(item.dataset.sourceId)) item.remove();
    });
    mergeSources.forEach((source, index) => {
      const item = ensureMergePreviewItem(layer, source);
      const rect = resolveSourcePreviewRect(source);
      item.style.left = `${rect.left}px`;
      item.style.top = `${rect.top}px`;
      item.style.width = `${rect.width}px`;
      item.style.height = `${rect.height}px`;
      item.style.maxWidth = `${rect.width}px`;
      item.style.maxHeight = `${rect.height}px`;
      item.style.zIndex = mergeSourcePreviewZIndex(source, index);
      item.title = `${index + 1}. ${fileName(source.asset?.path || "")}`;
    });
  }

  function clearMergeSourceCommitTimers({ clearPayloads = false } = {}) {
    currentMergeSourceCommitTimers().forEach((timerId) => windowObject.clearTimeout(timerId));
    currentMergeSourceCommitTimers().clear();
    if (clearPayloads) currentPendingMergeSourcePayloads().clear();
  }

  function scheduleMergeSourceCommit(payload) {
    const sourceId = payload?.source_id;
    if (!sourceId) return;
    currentPendingMergeSourcePayloads().set(sourceId, payload);
    const existingTimer = currentMergeSourceCommitTimers().get(sourceId);
    if (existingTimer !== undefined) windowObject.clearTimeout(existingTimer);
    const timerId = windowObject.setTimeout(() => {
      currentMergeSourceCommitTimers().delete(sourceId);
      const nextPayload = currentPendingMergeSourcePayloads().get(sourceId);
      currentPendingMergeSourcePayloads().delete(sourceId);
      if (nextPayload) callApi("/api/merge/source", nextPayload);
    }, 120);
    currentMergeSourceCommitTimers().set(sourceId, timerId);
  }

  async function flushPendingMergeSourceCommits({ keepalive = false } = {}) {
    if (currentPendingMergeSourcePayloads().size === 0) return;
    clearMergeSourceCommitTimers();
    const pendingPayloads = [...currentPendingMergeSourcePayloads().values()];
    currentPendingMergeSourcePayloads().clear();
    if (keepalive) {
      pendingPayloads.forEach((payload) => sendKeepaliveJson("/api/merge/source", payload));
      return;
    }
    for (const payload of pendingPayloads) {
      await callApi("/api/merge/source", payload);
    }
  }

  async function removeMergeSource(sourceId) {
    if (!sourceId) return;
    await flushPendingMergeSourceCommits();
    const pendingTimer = currentMergeSourceCommitTimers().get(sourceId);
    if (pendingTimer !== undefined) {
      windowObject.clearTimeout(pendingTimer);
      currentMergeSourceCommitTimers().delete(sourceId);
    }
    currentPendingMergeSourcePayloads().delete(sourceId);
    await callApi("/api/merge/remove", { source_id: sourceId });
  }

  function renderLocalMergePreview() {
    const video = $("primary-video");
    const stage = $("video-stage");
    if (!video || !stage) return;
    const mergeSources = currentState()?.project?.merge_sources || [];
    renderMergePreviewLayer(video, stage, mergeSources);
  }

  function renderMergeMediaList() {
    const list = $("merge-media-list");
    if (!list) return;
    const mergeSources = currentState()?.project?.merge_sources || [];
    const validSourceIds = new Set(mergeSources.map((source, index) => sourceIdentifier(source, String(index))));
    clearStaleMergeSourceTrimState(validSourceIds);
    [...currentMergeSourceExpansion().keys()].forEach((sourceId) => {
      if (sourceId !== pipDefaultsSectionId && !validSourceIds.has(sourceId)) currentMergeSourceExpansion().delete(sourceId);
    });
    withPreservedScrollState([list], () => {
      list.innerHTML = "";
      if (mergeSources.length === 0) {
        const empty = documentObject.createElement("div");
        empty.className = "hint";
          empty.textContent = "No added media yet. Add media to set roles, sync, and placement.";
        list.appendChild(empty);
        return;
      }

      mergeSources.forEach((source, index) => {
        const asset = source.asset || source;
        const sourceId = sourceIdentifier(source, String(index));
        const card = documentObject.createElement("div");
        card.className = "merge-media-card";
        card.dataset.sourceId = sourceId;
        const expanded = isMergeSourceExpanded(sourceId);
        card.classList.toggle("collapsed", !expanded);

        const header = documentObject.createElement("div");
        header.className = "merge-media-card-header";
        header.classList.add("section-header-with-toggle");
        const title = documentObject.createElement("strong");
        title.textContent = `${index + 1}. ${fileName(asset.path || "")}`;

        const toggle = documentObject.createElement("button");
        toggle.type = "button";
        toggle.className = "scoring-shot-toggle";
        toggle.textContent = expanded ? "v" : ">";
        toggle.title = expanded ? "Hide composition item controls" : "Show composition item controls";
        toggle.setAttribute("aria-label", `${expanded ? "Hide" : "Show"} composition item controls`);
        toggle.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          preserveElementViewportAnchor(
            () => documentObject.querySelector(`.merge-media-card[data-source-id="${sourceId}"]`),
            () => {
              setMergeSourceExpanded(sourceId, !expanded);
              renderMergeMediaList();
            },
          );
        });

        const remove = documentObject.createElement("button");
        remove.type = "button";
        remove.textContent = "Remove";
        remove.dataset.mergeSourceRemove = sourceId;
        remove.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          activity("merge.media.remove", { source_id: remove.dataset.mergeSourceRemove });
          void removeMergeSource(remove.dataset.mergeSourceRemove);
        });

        const headerActions = documentObject.createElement("div");
        headerActions.className = "merge-media-card-actions";
        headerActions.append(remove);
        header.append(toggle, title, headerActions);

        const meta = documentObject.createElement("small");
        meta.className = "merge-media-card-meta";
        const mediaType = asset.is_still_image ? "Image" : "Video";
        const dimensions = asset.width && asset.height ? ` • ${asset.width}x${asset.height}` : "";
        meta.textContent = `${mediaType}${dimensions}`;

        const trimSection = documentObject.createElement("section");
        trimSection.className = "settings-section merge-source-trim-section";
        const trimHeader = documentObject.createElement("div");
        trimHeader.className = "section-header sub-section-header";
        const trimTitle = documentObject.createElement("h3");
        trimTitle.textContent = "Trim Video";
        trimHeader.append(trimTitle);
        trimSection.append(trimHeader);

        const trimBusy = trimmingMergeSources.has(sourceId);
        const trimStatusState = currentMergeSourceTrimStatus(sourceId);
        const trimStatus = documentObject.createElement("p");
        trimStatus.className = trimStatusState?.tone === "error"
          ? "automation-error merge-source-trim-status"
          : "hint merge-source-trim-status";
        trimStatus.textContent = trimStatusState?.message || mergeSourceTrimHint(source);

        if (asset.is_still_image) {
          trimSection.append(trimStatus);
        } else {
          const trimDraft = mergeSourceTrimDraft(sourceId);
          const rememberTrimDraft = (field, value) => {
            updateMergeSourceTrimDraft(sourceId, { [field]: String(value ?? "") });
            setMergeSourceTrimStatus(sourceId, "");
          };
          const normalizeTrimDraftField = (field, value, options = {}) => {
            const normalized = normalizedTrimSecondsInputValue(value, options);
            updateMergeSourceTrimDraft(sourceId, { [field]: normalized });
            setMergeSourceTrimStatus(sourceId, "");
            return normalized;
          };

          const trimRangeGrid = documentObject.createElement("div");
          trimRangeGrid.className = "control-grid";

          const startField = documentObject.createElement("label");
          const startLabel = documentObject.createElement("span");
          startLabel.textContent = "Start (s)";
          const startInput = documentObject.createElement("input");
          startInput.type = "number";
          startInput.min = "0";
          startInput.step = "0.001";
          startInput.value = trimDraft.start_seconds;
          startInput.placeholder = "0.000";
          startInput.dataset.sourceId = sourceId;
          startInput.dataset.mergeSourceTrimField = "start_seconds";
          startInput.title = "Trim start time in seconds for this item.";
          startInput.disabled = trimBusy;
          startInput.addEventListener("input", () => rememberTrimDraft("start_seconds", startInput.value));
          startInput.addEventListener("change", () => {
            startInput.value = normalizeTrimDraftField("start_seconds", startInput.value, { fallback: "0.000" });
          });
          startField.append(startLabel, startInput);

          const endField = documentObject.createElement("label");
          const endLabel = documentObject.createElement("span");
          endLabel.textContent = "End (s)";
          const endInput = documentObject.createElement("input");
          endInput.type = "number";
          endInput.min = "0";
          endInput.step = "0.001";
          endInput.value = trimDraft.end_seconds;
          endInput.placeholder = "Leave blank";
          endInput.dataset.sourceId = sourceId;
          endInput.dataset.mergeSourceTrimField = "end_seconds";
          endInput.title = "Optional trim end time in seconds. Leave blank to keep the rest of the clip.";
          endInput.disabled = trimBusy;
          endInput.addEventListener("input", () => rememberTrimDraft("end_seconds", endInput.value));
          endInput.addEventListener("change", () => {
            endInput.value = normalizeTrimDraftField("end_seconds", endInput.value, { allowEmpty: true });
          });
          endField.append(endLabel, endInput);

          trimRangeGrid.append(startField, endField);

          const trimCaptureButtons = documentObject.createElement("div");
          trimCaptureButtons.className = "button-grid compact merge-source-trim-capture-buttons";

          const setStartFromPreview = documentObject.createElement("button");
          setStartFromPreview.type = "button";
          setStartFromPreview.textContent = "Use Current Frame As Start";
          setStartFromPreview.title = "Capture the current synced preview frame as this item's trim start.";
          setStartFromPreview.disabled = trimBusy;
          setStartFromPreview.addEventListener("click", () => {
            const nextValue = currentMergeSourceTrimCaptureValue(source);
            startInput.value = normalizeTrimDraftField("start_seconds", nextValue, { fallback: "0.000" });
          });

          const setEndFromPreview = documentObject.createElement("button");
          setEndFromPreview.type = "button";
          setEndFromPreview.textContent = "Use Current Frame As End";
          setEndFromPreview.title = "Capture the current synced preview frame as this item's trim end.";
          setEndFromPreview.disabled = trimBusy;
          setEndFromPreview.addEventListener("click", () => {
            const nextValue = currentMergeSourceTrimCaptureValue(source);
            endInput.value = normalizeTrimDraftField("end_seconds", nextValue, { allowEmpty: true });
          });

          const clearTrimEnd = documentObject.createElement("button");
          clearTrimEnd.type = "button";
          clearTrimEnd.textContent = "Clear End";
          clearTrimEnd.title = "Trim from the chosen start through the end of the clip.";
          clearTrimEnd.disabled = trimBusy;
          clearTrimEnd.addEventListener("click", () => {
            endInput.value = normalizeTrimDraftField("end_seconds", "", { allowEmpty: true });
          });

          trimCaptureButtons.append(setStartFromPreview, setEndFromPreview, clearTrimEnd);

          const trimActionButtons = documentObject.createElement("div");
          trimActionButtons.className = "button-grid two-up merge-source-trim-actions";

          const trimButton = documentObject.createElement("button");
          trimButton.type = "button";
          trimButton.className = "primary-button";
          trimButton.textContent = trimBusy ? "Trimming..." : "Trim Video";
          trimButton.title = String(currentState()?.project?.path || "").trim()
            ? "Create or refresh this item's local trim derivative."
            : "Save or create a project folder before trimming added media.";
          trimButton.disabled = trimBusy || !String(currentState()?.project?.path || "").trim();
          trimButton.addEventListener("click", () => {
            void trimMergeSource(sourceId);
          });

          const resetTrimRange = documentObject.createElement("button");
          resetTrimRange.type = "button";
          resetTrimRange.textContent = "Reset Range";
          resetTrimRange.title = "Restore this item's trim inputs to the full source range.";
          resetTrimRange.disabled = trimBusy;
          resetTrimRange.addEventListener("click", () => {
            startInput.value = normalizeTrimDraftField("start_seconds", "0.000", { fallback: "0.000" });
            endInput.value = normalizeTrimDraftField("end_seconds", "", { allowEmpty: true });
          });

          trimActionButtons.append(trimButton, resetTrimRange);
          trimSection.append(trimRangeGrid, trimCaptureButtons, trimActionButtons, trimStatus);
        }

        const controls = documentObject.createElement("div");
        controls.className = "merge-source-controls";
        const syncRow = documentObject.createElement("div");
        syncRow.className = "merge-source-sync-row";

        const placementValue = currentSourcePlacementValue(source);
        const placementSection = documentObject.createElement("section");
        placementSection.className = "settings-section merge-source-placement-section";
        placementSection.dataset.sourceId = sourceId;
        const placementHeader = documentObject.createElement("div");
        placementHeader.className = "section-header sub-section-header";
        const placementTitle = documentObject.createElement("h3");
        placementTitle.textContent = "Placement";
        placementHeader.append(placementTitle);

        const placementGrid = documentObject.createElement("div");
        placementGrid.className = "control-grid";

        const placementModeField = documentObject.createElement("label");
        placementModeField.className = "merge-source-field";
        const placementModeText = documentObject.createElement("span");
        placementModeText.textContent = "Placement mode";
        const placementModeSelect = documentObject.createElement("select");
        placementModeSelect.dataset.mergeSourceField = "placement_mode";
        placementModeSelect.dataset.sourceId = sourceId;
        placementModeSelect.title = "Choose whether this item acts as a base, panel, or PiP overlay.";
        mergeSourcePlacementModeOptions.forEach((optionValue) => {
          const option = documentObject.createElement("option");
          option.value = optionValue.value;
          option.textContent = optionValue.label;
          placementModeSelect.appendChild(option);
        });
        syncControlValue(placementModeSelect, placementValue.mode);
        placementModeField.append(placementModeText, placementModeSelect);

        const placementSlotField = documentObject.createElement("label");
        placementSlotField.className = "merge-source-field";
        const placementSlotText = documentObject.createElement("span");
        placementSlotText.textContent = "Placement slot";
        const placementSlotSelect = documentObject.createElement("select");
        placementSlotSelect.dataset.mergeSourceField = "placement_slot";
        placementSlotSelect.dataset.sourceId = sourceId;
        placementSlotSelect.title = "Choose the side, band, or overlay position for this item's placement.";
        syncPlacementSlotControl(placementSlotSelect, {
          mode: placementValue.mode,
          source,
          value: placementValue.slot,
        });
        placementSlotField.append(placementSlotText, placementSlotSelect);

        const placementTargetKindField = documentObject.createElement("label");
        placementTargetKindField.className = "merge-source-field";
        const placementTargetKindText = documentObject.createElement("span");
        placementTargetKindText.textContent = "Overlay target";
        const placementTargetKindSelect = documentObject.createElement("select");
        placementTargetKindSelect.dataset.mergeSourceField = "target_kind";
        placementTargetKindSelect.dataset.sourceId = sourceId;
        placementTargetKindSelect.title = "Choose whether this overlay sits over the primary video or another added item.";
        [
          { value: "primary_video", label: "Primary video" },
          { value: "merge_source", label: "Added media item" },
        ].forEach((optionValue) => {
          const option = documentObject.createElement("option");
          option.value = optionValue.value;
          option.textContent = optionValue.label;
          placementTargetKindSelect.appendChild(option);
        });
        syncControlValue(placementTargetKindSelect, placementValue.target_kind);
        placementTargetKindField.append(placementTargetKindText, placementTargetKindSelect);

        const placementTargetSourceField = documentObject.createElement("label");
        placementTargetSourceField.className = "merge-source-field";
        const placementTargetSourceText = documentObject.createElement("span");
        placementTargetSourceText.textContent = "Base item";
        const placementTargetSourceSelect = documentObject.createElement("select");
        placementTargetSourceSelect.dataset.mergeSourceField = "target_source_id";
        placementTargetSourceSelect.dataset.sourceId = sourceId;
        placementTargetSourceSelect.title = "Choose which added item acts as the visible base for this overlay.";
        syncPlacementTargetSourceControl(placementTargetSourceSelect, {
          source,
          value: placementValue.target_source_id,
        });
        placementTargetSourceField.append(placementTargetSourceText, placementTargetSourceSelect);

        let layerXField = null;
        let layerYField = null;

        const syncFreeformPositionFields = (activeSource = source, placement = null) => {
          const usesPreviewDrag = mergeSourcePlacementUsesPreviewDrag(activeSource, placement);
          if (layerXField) layerXField.hidden = !usesPreviewDrag;
          if (layerYField) layerYField.hidden = !usesPreviewDrag;
        };

        const refreshPlacementSection = ({ preferredSlot = null } = {}) => {
          const activeSource = mergeSourceById(sourceId) || source;
          syncPlacementSlotControl(placementSlotSelect, {
            mode: placementModeSelect.value,
            source: activeSource,
            value: preferredSlot ?? placementSlotSelect.value,
          });
          const targetOptions = mergeSourcePlacementTargetSourceOptions(activeSource);
          const mergeSourceOption = placementTargetKindSelect.querySelector('option[value="merge_source"]');
          if (mergeSourceOption) mergeSourceOption.disabled = targetOptions.length === 0;
          syncPlacementTargetSourceControl(placementTargetSourceSelect, {
            source: activeSource,
            value: placementTargetSourceSelect.value,
          });
          const supportsTargetSelection = mergeSourcePlacementSupportsTargetSelection(
            placementModeSelect.value,
            activeSource,
          );
          if (
            supportsTargetSelection
            && placementTargetKindSelect.value === "merge_source"
            && !resolvedPlacementTargetSourceIdValue(placementTargetSourceSelect.value, activeSource)
            && targetOptions.length > 0
          ) {
            syncPlacementTargetSourceControl(placementTargetSourceSelect, {
              source: activeSource,
              value: targetOptions[0].value,
            });
          }
          if (
            supportsTargetSelection
            && placementTargetKindSelect.value === "merge_source"
            && targetOptions.length === 0
          ) {
            syncControlValue(placementTargetKindSelect, "primary_video");
          }
          placementTargetKindField.hidden = !supportsTargetSelection;
          placementTargetSourceField.hidden = !supportsTargetSelection || placementTargetKindSelect.value !== "merge_source";
          const nextPlacement = {
            mode: placementModeSelect.value,
            slot: placementSlotSelect.value,
            target_kind: placementTargetKindSelect.value,
            target_source_id: placementTargetSourceSelect.value,
          };
          syncFreeformPositionFields(activeSource, nextPlacement);
        };

        placementModeSelect.addEventListener("change", () => {
          refreshPlacementSection();
          scheduleMergeSourceCommit(previewSourceUpdate());
        });
        placementSlotSelect.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
        placementTargetKindSelect.addEventListener("change", () => {
          refreshPlacementSection();
          scheduleMergeSourceCommit(previewSourceUpdate());
        });
        placementTargetSourceSelect.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));

        placementGrid.append(
          placementModeField,
          placementSlotField,
          placementTargetKindField,
          placementTargetSourceField,
        );
        placementSection.append(placementHeader, placementGrid);

        const readSourcePayload = () => {
          const roleControl = controls.querySelector('[data-merge-source-field="camera_role"]');
          const nextSize = clampNumber(Number(controls.querySelector('[data-merge-source-field="size"]')?.value) || 35, 1, 95);
          const nextX = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="x"]')?.value) ?? 1;
          const nextY = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="y"]')?.value) ?? 1;
          const opacityControl = controls.querySelector('[data-merge-source-field="opacity"]');
          const nextOpacity = opacityControl ? opacityValueFromPercent(opacityControl.value) : currentSourceOpacity(source);
          return {
            source_id: sourceId,
            camera_role: normalizedAngleRoleValue(roleControl?.value, source),
            pip_size_percent: nextSize,
            pip_x: nextX,
            pip_y: nextY,
            opacity: nextOpacity,
            placement: readSourcePlacementPayload(card, source),
          };
        };

        const previewSourceUpdate = () => {
          const payload = readSourcePayload();
          updateLocalMergeSourcePosition(
            sourceId,
            payload.pip_x,
            payload.pip_y,
            payload.pip_size_percent,
            payload.opacity,
            payload.camera_role,
            payload.placement,
            { reseedRolePlacement: true },
          );
          renderLocalMergePreview();
          return mergeSourcePositionPayload(sourceId, mergeSourceById(sourceId));
        };

        const buildSourceRoleSelect = () => {
          const label = documentObject.createElement("label");
          label.className = "merge-source-field";
          const text = documentObject.createElement("span");
          text.textContent = "Camera role";
          const select = documentObject.createElement("select");
          select.dataset.mergeSourceField = "camera_role";
          select.dataset.sourceId = sourceId;
          select.title = "Track which camera role this item fills: primary, follow, static, or detail.";
          mergeSourceAngleRoles.forEach((role) => {
            const option = documentObject.createElement("option");
            option.value = role.value;
            option.textContent = role.label;
            select.appendChild(option);
          });
          syncControlValue(select, currentSourceAngleRole(source));
          select.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
          label.append(text, select);
          return label;
        };

        const buildSourceNumberInput = (labelText, field, value, min, max, step, titleText) => {
          const label = documentObject.createElement("label");
          label.className = "merge-source-field";
          const text = documentObject.createElement("span");
          text.textContent = labelText;
          const input = documentObject.createElement("input");
          input.type = "number";
          input.min = String(min);
          input.max = String(max);
          input.step = String(step);
          input.value = value;
          input.dataset.mergeSourceField = field;
          input.dataset.sourceId = sourceId;
          input.title = titleText;
          input.addEventListener("input", previewSourceUpdate);
          input.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
          input.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
          label.append(text, input);
          return label;
        };

        const sizeField = documentObject.createElement("label");
        sizeField.className = "merge-source-field merge-source-size-field";
        const sizeText = documentObject.createElement("span");
        sizeText.textContent = "Layer size";
        const sizeControl = documentObject.createElement("span");
        sizeControl.className = "pip-size-control";
        const sizeInput = documentObject.createElement("input");
        sizeInput.type = "range";
        sizeInput.min = "1";
        sizeInput.max = "95";
        sizeInput.step = "1";
        sizeInput.value = String(currentPipSizePercent(source));
        sizeInput.dataset.mergeSourceField = "size";
        sizeInput.dataset.sourceId = sourceId;
        sizeInput.title = "1 is smallest, 95 is largest.";
        sizeInput.addEventListener("input", () => {
          const output = sizeField.querySelector('[data-merge-source-output="size"]');
          if (output) output.textContent = `${sizeInput.value}%`;
          previewSourceUpdate();
        });
        sizeInput.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
        sizeInput.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
        const sizeOutput = documentObject.createElement("output");
        sizeOutput.dataset.mergeSourceOutput = "size";
        sizeOutput.dataset.sourceId = sourceId;
        sizeOutput.textContent = `${sizeInput.value}%`;
        sizeControl.append(sizeInput, sizeOutput);
        sizeField.append(sizeText, sizeControl);

        const buildSourceOpacityInput = () => {
          const label = documentObject.createElement("label");
          label.className = "merge-source-field merge-source-opacity-field";
          const text = documentObject.createElement("span");
          text.textContent = "Layer opacity";
          const percentField = documentObject.createElement("span");
          percentField.className = "opacity-percent-field";
          const input = documentObject.createElement("input");
          input.type = "number";
          input.className = "opacity-percent-input";
          input.min = "0";
          input.max = "100";
          input.step = "1";
          input.value = String(opacityPercentValue(currentSourceOpacity(source)));
          input.dataset.mergeSourceField = "opacity";
          input.dataset.sourceId = sourceId;
          input.title = "0 is transparent, 100 is opaque.";
          input.addEventListener("input", previewSourceUpdate);
          input.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
          input.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
          const suffix = documentObject.createElement("span");
          suffix.className = "opacity-percent-suffix";
          suffix.textContent = "%";
          percentField.append(input, suffix);
          label.append(text, percentField);
          return label;
        };

        const syncLabel = documentObject.createElement("small");
        syncLabel.className = "merge-source-sync-label";
        syncLabel.dataset.mergeSourceSyncLabel = "true";
        syncLabel.dataset.sourceId = sourceId;
        syncLabel.textContent = formatSyncOffsetLabel(currentSourceSyncOffsetMs(source));

        const syncStatus = documentObject.createElement("small");
        syncStatus.className = "merge-source-sync-hint";
        syncStatus.textContent = sourceSyncStatusLabel(source);

        const syncButtons = documentObject.createElement("div");
        syncButtons.className = "button-grid compact merge-source-sync-buttons";
        [-10, -1, 1, 10].forEach((deltaMs) => {
          const button = documentObject.createElement("button");
          button.type = "button";
          button.textContent = `${deltaMs > 0 ? "+" : ""}${deltaMs}`;
          button.title = `Nudge this composition item ${deltaMs > 0 ? "later" : "earlier"} by ${Math.abs(deltaMs)} ms.`;
          button.addEventListener("click", () => {
            const nextOffset = currentSourceSyncOffsetMs(mergeSourceById(sourceId)) + deltaMs;
            updateLocalMergeSourceSyncOffset(sourceId, nextOffset);
            renderVideo();
            callApi("/api/merge/source", { source_id: sourceId, sync_delta_ms: deltaMs });
          });
          syncButtons.appendChild(button);
        });

        if (source.supports_sync_analysis) {
          const analyzeButton = documentObject.createElement("button");
          analyzeButton.type = "button";
          analyzeButton.textContent = source.sync_analysis_status === "ready" ? "Re-run beep sync" : "Analyze beep sync";
          analyzeButton.disabled = source.sync_analysis_status === "running";
          analyzeButton.title = "Use ShotML to find this added media clip's start beep and set sync automatically.";
          analyzeButton.addEventListener("click", () => {
            void (async () => {
              await flushPendingMergeSourceCommits();
              callApi("/api/merge/source/analyze", { source_id: sourceId });
            })();
          });
          syncButtons.appendChild(analyzeButton);
        }

        controls.append(
          buildSourceRoleSelect(),
          sizeField,
          buildSourceOpacityInput(),
          (layerXField = buildSourceNumberInput("Layer X", "x", normalizedCoordinateValue(source.pip_x) ?? 1, 0, 1, 0.01, "0 is left, 1 is right.")),
          (layerYField = buildSourceNumberInput("Layer Y", "y", normalizedCoordinateValue(source.pip_y) ?? 1, 0, 1, 0.01, "0 is top, 1 is bottom.")),
        );

        refreshPlacementSection();

        syncRow.append(syncLabel, syncButtons, syncStatus);

        const body = documentObject.createElement("div");
        body.className = "merge-media-card-body";
        body.hidden = !expanded;
        body.append(meta, trimSection, placementSection, controls, syncRow);
        card.append(header, body);
        syncMergeSourceControls(
          sourceId,
          normalizedCoordinateValue(source.pip_x),
          normalizedCoordinateValue(source.pip_y),
          currentPipSizePercent(source),
          currentSourceSyncOffsetMs(source),
          currentSourceOpacity(source),
          currentSourceAngleRole(source),
          source.placement,
        );
        list.appendChild(card);
      });
    });
  }

  function readMergePayload() {
    const pipValue = Number($("pip-size").value);
    return {
      enabled: $("merge-enabled").checked,
      layout: $("merge-layout").value,
      pip_size_percent: Number.isFinite(pipValue) ? clampNumber(pipValue, 1, 95) : 35,
      pip_x: normalizedCoordinateValue($("pip-x").value) ?? 1,
      pip_y: normalizedCoordinateValue($("pip-y").value) ?? 1,
    };
  }

  function scheduleMergeApply() {
    const payload = readMergePayload();
    applyMergeDraft(payload);
    autoApplyMerge(payload);
  }

  return Object.freeze({
    normalizeMergeDraftValue,
    applyMergeDraft,
    mergeMergeDraft,
    mergePendingMergeSourcePayloads,
    currentPipSizePercent,
    sourceIdentifier,
    currentSourceSyncOffsetMs,
    currentSourceOpacity,
    formatSyncOffsetLabel,
    mergePreviewTargetTime,
    mergeSourceById,
    isMergeSourceExpanded,
    setMergeSourceExpanded,
    syncMergeSourceControls,
    updateLocalMergeSourcePosition,
    updateLocalMergeSourceSyncOffset,
    mergeSourcePositionPayload,
    syncMergePreviewStateFromControls,
    mergeSourcePipRect,
    ensureMergePreviewItem,
    renderMergePreviewLayer,
    clearMergeSourceCommitTimers,
    scheduleMergeSourceCommit,
    flushPendingMergeSourceCommits,
    hydrateMergeSourcesFromDefaults,
    renderMergeMediaList,
    renderLocalMergePreview,
    readMergePayload,
    scheduleMergeApply,
  });
}
