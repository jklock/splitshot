export function createMarkersPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  getActiveTool = () => "project",
  getSelectedShotId = () => null,
  getPopupBubbleExpansion = () => new Map(),
  getSelectedPopupBubbleId = () => null,
  setSelectedPopupBubbleIdValue = () => {},
  getSelectedPopupKeyframeOffsetMs = () => 0,
  setSelectedPopupKeyframeOffsetValue = () => {},
  getSelectedPopupPlacementMode = () => "base",
  setSelectedPopupPlacementModeValue = () => {},
  getPopupFilterMode = () => "all",
  setPopupFilterModeValue = () => {},
  getPopupAuthoringCollapsed = () => false,
  setPopupAuthoringCollapsedValue = () => {},
  getPopupBubbleDrag = () => null,
  setPopupBubbleDrag = () => {},
  getPopupAutoTraceBubbleId = () => null,
  getPopupGeneratedMotionOffsetsByBubbleId = () => new Map(),
  getPopupMotionGenerationSummaryByBubbleId = () => new Map(),
  normalizePopupBubble = (bubble) => bubble,
  currentPopupTemplate = () => ({}),
  popupBubbles = () => [],
  createPopupBubbleId = () => "popup-bubble",
  defaultScoreLetter = () => "",
  seekPrimaryVideoToTimeMs = () => false,
  popupBubbleSeekTimeMs = () => 0,
  revealPopupBubbleCard = () => {},
  popupDefaultDurationMsForShot = (_shot, template) => Math.max(1, Math.round(Number(template?.duration_ms ?? 1000) || 1000)),
  popupTemplateTextForShot = () => "",
  orderedShotsByTime = () => [],
  timingSegmentForShot = () => null,
  shotById = () => null,
  compactScoreDisplay = (value) => value,
  activeScoringRuleset = () => null,
  popupTextForShotId = () => "",
  defaultPopupShotId = () => null,
  clampPopupDurationForShot = (durationMs) => durationMs,
  popupBubbleMotionPath = (bubble) => Array.isArray(bubble?.motion_path) ? bubble.motion_path : [],
  scaledPopupMotionPathOffsets = (path) => path,
  normalizePopupMotionPath = (path) => path,
  normalizePopupMotionMode = (mode) => mode,
  normalizePopupQuadrant = (value) => value,
  popupBubblePoint = () => ({ x: 0.5, y: 0.5 }),
  popupBubbleEffectiveTimeMs = () => 0,
  popupBubbleResolvedText = () => "",
  popupBubbleIsVisibleAtPosition = () => false,
  popupBubbleRenderPositionMs = (_bubble, positionMs) => positionMs,
  popupBubblePlacementSelectorStyle = () => null,
  popupBubbleRenderStyle = () => ({ background_color: "#000000", text_color: "#ffffff", font_weight: 600 }),
  resolvedPopupBubbleSize = () => ({ width: 160, height: 64 }),
  scaledOverlayPixelValue = (value) => value,
  popupBubbleImageUrl = () => "",
  popupKeyframeEasing = (value) => value || "linear",
  popupBubbleMotionPointAtOffset = (_path, _offsetMs, basePoint) => basePoint,
  popupMotionModeValueForUiMode = (uiMode) => uiMode,
  popupBubbleMotionUiMode = () => "fixed",
  popupMotionOffsetIsGenerated = () => false,
  popupGeneratedMotionOffsetsForBubbleId = () => [],
  setPopupMotionGeneratedOffsets = () => {},
  prunePopupMotionUiState = () => {},
  renderPopupEditors = () => {},
  renderLiveOverlay = () => {},
  render = () => {},
  callApi = () => {},
  setStatus = () => {},
  activity = () => {},
  setActiveTool = () => {},
  controlIsActive = () => false,
  syncControlValue = () => {},
  syncControlChecked = () => {},
  setPopupEditorSectionExpanded = () => {},
  copyPopupMotionUiState = () => {},
  precise = (value) => String(value ?? ""),
  clamp = (value, minimum, maximum) => Math.min(Math.max(value, minimum), maximum),
  normalizedCoordinateValue = (value) => value,
  previewFrameClientRect = () => null,
  overlayRenderPositionMs = () => 0,
  resolveNormalizedPointFromRect = () => null,
  capturePointer = () => {},
  releasePointer = () => {},
  placeOverlayBadge = () => {},
  rgba = (color) => color,
  capturePopupWorkbenchRestoreState = () => {},
  cancelOverlayDragInteractions = () => {},
  stagePopupImagePath = (path) => path,
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  scheduleReviewStageRestore = () => {},
  primaryFrameDurationMs = () => 0,
  popupMotionSuggestedInBetweenCount = () => ({ count: 0, distancePx: 0 }),
  popupMotionAutoOffsets = () => [],
  popupMotionSamplePointForOffset = (_bubble, _offsetMs, _finishOffsetMs, startPoint) => startPoint,
  popupMotionNextDetailOffsetMs = () => null,
  autoTracePopupBubbleMotion = async () => false,
  VALID_POPUP_FILTER_MODES = new Set(["all"]),
  CUSTOM_QUADRANT_VALUE = "custom",
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function currentActiveTool() {
    return String(getActiveTool() || "project");
  }

  function selectedShotId() {
    return getSelectedShotId() || null;
  }

  function popupBubbleExpansion() {
    return getPopupBubbleExpansion() || new Map();
  }

  function selectedPopupBubbleId() {
    return getSelectedPopupBubbleId() || null;
  }

  function setSelectedPopupBubbleId(nextValue) {
    setSelectedPopupBubbleIdValue(nextValue ? String(nextValue) : null);
  }

  function selectedPopupKeyframeOffsetMs() {
    return Math.max(0, Math.round(Number(getSelectedPopupKeyframeOffsetMs()) || 0));
  }

  function setSelectedPopupKeyframeOffsetState(nextValue) {
    setSelectedPopupKeyframeOffsetValue(Math.max(0, Math.round(Number(nextValue) || 0)));
  }

  function selectedPopupPlacementMode() {
    return getSelectedPopupPlacementMode() === "keyframe" ? "keyframe" : "base";
  }

  function setSelectedPopupPlacementModeState(nextValue) {
    setSelectedPopupPlacementModeValue(nextValue === "keyframe" ? "keyframe" : "base");
  }

  function popupFilterMode() {
    return String(getPopupFilterMode() || "all");
  }

  function setPopupFilterModeState(nextValue) {
    setPopupFilterModeValue(nextValue);
  }

  function popupAuthoringCollapsed() {
    return Boolean(getPopupAuthoringCollapsed());
  }

  function popupBubbleDrag() {
    return getPopupBubbleDrag() || null;
  }

  function popupGeneratedMotionOffsetsByBubbleId() {
    return getPopupGeneratedMotionOffsetsByBubbleId() || new Map();
  }

  function popupMotionGenerationSummaryByBubbleId() {
    return getPopupMotionGenerationSummaryByBubbleId() || new Map();
  }

  function markersWorkbenchShown() {
    return Boolean($("cockpit-root")?.classList.contains("markers-expanded"));
  }

  function popupEditingActive() {
    return currentActiveTool() === "markers" && markersWorkbenchShown();
  }

  function popupShotPenaltyCounts(shotId) {
    const segment = timingSegmentForShot(shotId);
    const shot = shotById(shotId);
    return segment?.penalty_counts || shot?.score?.penalty_counts || {};
  }

  function popupShotHasPenaltySignal(shotId) {
    const counts = popupShotPenaltyCounts(shotId);
    if (Object.values(counts).some((value) => Number(value || 0) > 0)) return true;
    const text = String(popupTextForShotId(shotId) || "").toUpperCase();
    return /\b(M|NS|NT|PE|FP|FTDR|FPE|PM|SPF|SND)\b/.test(text);
  }

  function popupShotHasScoringSignal(shotId) {
    if (popupShotHasPenaltySignal(shotId)) return true;
    const segment = timingSegmentForShot(shotId);
    const shot = shotById(shotId);
    const rawLetter = segment?.score_letter || shot?.score?.letter?.value || shot?.score?.letter || "";
    const scoreLetter = compactScoreDisplay(rawLetter, activeScoringRuleset());
    return Boolean(scoreLetter && scoreLetter !== defaultScoreLetter());
  }

  function selectPopupBubble(bubbleId, {
    seek = true,
    reveal = true,
    focus = false,
    activateTool = false,
    expand = false,
    rerender = true,
  } = {}) {
    const previousBubbleId = selectedPopupBubbleId();
    const bubble = popupBubbles().find((item) => item.id === bubbleId) || null;
    if (!bubble) {
      setSelectedPopupBubbleId(null);
      setSelectedPopupPlacementMode("base");
      return false;
    }
    setSelectedPopupBubbleId(bubble.id);
    if (previousBubbleId !== bubble.id) setSelectedPopupPlacementMode("base");
    if (expand) {
      if (!popupBubbleExpansion().has(bubble.id)) {
        popupBubbleExpansion().set(bubble.id, true);
      } else if (!popupBubbleExpansion().get(bubble.id)) {
        popupBubbleExpansion().set(bubble.id, true);
      }
    }
    if (activateTool) setActiveTool("markers");
    if (rerender) renderPopupEditors();
    if (seek) seekPrimaryVideoToTimeMs(popupBubbleSeekTimeMs(bubble));
    if (reveal) windowObject.requestAnimationFrame(() => revealPopupBubbleCard(bubble.id, { focus }));
    return true;
  }

  function selectPopupBubbleForShot(shotId, options = {}) {
    if (!shotId) return false;
    const matchingBubble = popupBubbles().find((bubble) => bubble.anchor_mode === "shot" && bubble.shot_id === shotId) || null;
    if (!matchingBubble) return false;
    return selectPopupBubble(matchingBubble.id, options);
  }

  function selectedPopupBubble() {
    if (!selectedPopupBubbleId()) return null;
    return popupBubbles().find((bubble) => bubble.id === selectedPopupBubbleId()) || null;
  }

  function setSelectedPopupPlacementMode(mode, offsetMs = selectedPopupKeyframeOffsetMs()) {
    const nextMode = mode === "keyframe" ? "keyframe" : "base";
    setSelectedPopupPlacementModeState(nextMode);
    if (nextMode === "keyframe") {
      setSelectedPopupKeyframeOffsetState(Math.max(0, Math.round(Number(offsetMs) || 0)));
      return;
    }
    setSelectedPopupKeyframeOffsetState(0);
  }

  function popupPlacementSummary(bubble) {
    if (!bubble) return "Base point";
    if (selectedPopupPlacementMode() !== "keyframe") return "Base point";
    return selectedPopupKeyframeOffsetMs() <= 0
      ? "Base point"
      : `Step ${precise(selectedPopupKeyframeOffsetMs())}s`;
  }

  function setPopupBubbles(bubbles, { commit = true, rerender = true } = {}) {
    if (!currentState().project) return;
    currentState().project.popups = bubbles.map((bubble) => normalizePopupBubble(bubble));
    if (selectedPopupBubbleId() && !currentState().project.popups.some((bubble) => bubble.id === selectedPopupBubbleId())) {
      setSelectedPopupBubbleId(null);
    }
    prunePopupMotionUiState(currentState().project.popups);
    if (rerender) renderPopupEditors();
    renderLiveOverlay();
    if (commit) callApi("/api/popups", { popups: currentState().project.popups });
  }

  function syncPopupBubbleSizeControls(bubbleId) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return;
    const card = [...documentObject.querySelectorAll(".popup-bubble-card[data-popup-id]")].find(
      (element) => element instanceof HTMLElement && element.dataset.popupId === bubbleId,
    );
    if (!(card instanceof HTMLElement)) return;
    const displayedSize = resolvedPopupBubbleSize(bubble);
    const widthInput = card.querySelector('[data-popup-field="width"]');
    const heightInput = card.querySelector('[data-popup-field="height"]');
    if (widthInput instanceof HTMLInputElement && !controlIsActive(widthInput)) syncControlValue(widthInput, displayedSize.width);
    if (heightInput instanceof HTMLInputElement && !controlIsActive(heightInput)) syncControlValue(heightInput, displayedSize.height);
  }

  function setPopupBubbleField(bubbleId, field, rawValue, options = {}) {
    const nextBubbles = popupBubbles().map((bubble) => {
      if (bubble.id !== bubbleId) return bubble;
      const previousDurationMs = Math.max(1, Math.round(Number(bubble.duration_ms ?? 1000) || 1000));
      const nextBubble = normalizePopupBubble({
        ...bubble,
        [field]: rawValue,
        ...(field === "x" || field === "y" ? { quadrant: CUSTOM_QUADRANT_VALUE } : {}),
      });
      if (field === "follow_motion") {
        nextBubble.follow_motion = Boolean(rawValue);
        nextBubble.motion_mode = nextBubble.follow_motion ? "guided" : "fixed";
        if (nextBubble.follow_motion) setPopupEditorSectionExpanded("motion", true);
        if (!nextBubble.follow_motion) {
          setPopupMotionGeneratedOffsets(bubble.id, []);
          popupMotionGenerationSummaryByBubbleId().delete(bubble.id);
          if (bubble.id === selectedPopupBubbleId()) setSelectedPopupPlacementMode("base");
        }
      }
      if (field === "motion_mode") {
        nextBubble.motion_mode = normalizePopupMotionMode(rawValue, nextBubble.follow_motion, nextBubble.motion_path);
        nextBubble.follow_motion = nextBubble.motion_mode !== "fixed";
        if (nextBubble.follow_motion) setPopupEditorSectionExpanded("motion", true);
        if (!nextBubble.follow_motion) {
          setPopupMotionGeneratedOffsets(bubble.id, []);
          popupMotionGenerationSummaryByBubbleId().delete(bubble.id);
          if (bubble.id === selectedPopupBubbleId()) setSelectedPopupPlacementMode("base");
        }
      }
      if (field === "anchor_mode") {
        nextBubble.anchor_mode = rawValue === "shot" ? "shot" : "time";
        nextBubble.shot_id = nextBubble.anchor_mode === "shot" ? (nextBubble.shot_id || defaultPopupShotId()) : null;
        if (nextBubble.anchor_mode === "shot" && !nextBubble.shot_id) nextBubble.anchor_mode = "time";
      }
      if (field === "shot_id") {
        nextBubble.shot_id = rawValue ? String(rawValue) : null;
        nextBubble.anchor_mode = nextBubble.shot_id ? "shot" : "time";
      }
      if (field === "time_ms") {
        nextBubble.time_ms = Math.max(0, Math.round(Number(rawValue) || 0));
        nextBubble.anchor_mode = "time";
        nextBubble.shot_id = null;
      }
      if (field !== "image_path" && nextBubble.image_path) {
        nextBubble.image_path = stagePopupImagePath(nextBubble.image_path);
      }
      const rawNextDurationMs = Math.max(1, Math.round(Number(nextBubble.duration_ms ?? 1000) || 1000));
      const shotLinkChanged = field === "anchor_mode"
        || field === "shot_id"
        || (bubble.anchor_mode !== "shot" && nextBubble.anchor_mode === "shot")
        || (bubble.shot_id || null) !== (nextBubble.shot_id || null);
      const nextDurationMs = shotLinkChanged && nextBubble.anchor_mode === "shot" && nextBubble.shot_id
        ? clampPopupDurationForShot(rawNextDurationMs, nextBubble.shot_id, null, nextBubble.time_ms)
        : rawNextDurationMs;
      const durationChanged = nextDurationMs !== previousDurationMs;
      nextBubble.duration_ms = nextDurationMs;
      if (durationChanged && popupBubbleMotionPath(bubble).length > 0) {
        if (nextBubble.follow_motion) {
          nextBubble.motion_path = scaledPopupMotionPathOffsets(popupBubbleMotionPath(bubble), previousDurationMs, nextBubble.duration_ms);
        } else {
          nextBubble.motion_path = normalizePopupMotionPath(popupBubbleMotionPath(bubble).map((point) => ({
            ...point,
            offset_ms: Math.max(1, Math.min(nextBubble.duration_ms, point.offset_ms)),
          })));
        }
      } else if (nextBubble.motion_path.length > 0) {
        nextBubble.motion_path = normalizePopupMotionPath(popupBubbleMotionPath(nextBubble).map((point) => ({
          ...point,
          offset_ms: Math.max(1, Math.min(nextBubble.duration_ms, point.offset_ms)),
        })));
      }
      nextBubble.motion_mode = normalizePopupMotionMode(nextBubble.motion_mode, nextBubble.follow_motion, nextBubble.motion_path);
      if (durationChanged && popupMotionGenerationSummaryByBubbleId().has(bubble.id)) {
        popupMotionGenerationSummaryByBubbleId().set(bubble.id, "Start or Finish changed — regenerate to refresh the in-between steps.");
      }
      if (field === "quadrant") nextBubble.quadrant = normalizePopupQuadrant(rawValue, nextBubble.x, nextBubble.y);
      if (nextBubble.anchor_mode === "shot" && nextBubble.shot_id && nextBubble.content_type === "text") {
        nextBubble.text = popupTextForShotId(nextBubble.shot_id) || nextBubble.text;
      }
      return nextBubble;
    });
    setPopupBubbles(nextBubbles, options);
    if (field !== "enabled") setSelectedPopupBubbleId(bubbleId);
    if ((field === "anchor_mode" || field === "shot_id") && currentState().media?.primary_available) {
      const updatedBubble = popupBubbles().find((bubble) => bubble.id === bubbleId);
      if (updatedBubble?.anchor_mode === "shot" && updatedBubble.shot_id) {
        selectPopupBubble(updatedBubble.id, { seek: true, reveal: true, focus: false, activateTool: false });
      }
    }
    if (["text", "quadrant", "width", "height"].includes(field)) syncPopupBubbleSizeControls(bubbleId);
  }

  function currentPrimaryVideoPositionMs() {
    const video = $("primary-video");
    return Math.max(0, Math.round((video?.currentTime || 0) * 1000));
  }

  function addPopupBubble(overrides = {}) {
    const template = currentPopupTemplate();
    const nextBubble = normalizePopupBubble({
      id: createPopupBubbleId(),
      name: "",
      text: template.content_type === "image" ? "" : defaultScoreLetter(),
      anchor_mode: "time",
      shot_id: null,
      time_ms: currentPrimaryVideoPositionMs(),
      duration_ms: template.duration_ms,
      quadrant: template.quadrant,
      x: 0.5,
      y: 0.5,
      enabled: template.enabled,
      width: template.width,
      height: template.height,
      follow_motion: template.follow_motion,
      motion_mode: template.motion_mode,
      content_type: template.content_type,
      image_path: template.image_path,
      image_scale_mode: template.image_scale_mode,
      background_color: template.background_color,
      text_color: template.text_color,
      opacity: template.opacity,
      ...overrides,
    });
    setPopupBubbles([...popupBubbles(), nextBubble], { commit: true, rerender: true });
    selectPopupBubble(nextBubble.id, { seek: false, reveal: true, focus: true, activateTool: true, expand: true });
    return nextBubble;
  }

  function popupShotMatchesImportMode(shot, mode) {
    if (!shot?.id) return false;
    if (mode === "scored") return popupShotHasScoringSignal(shot.id);
    if (mode === "penalty") return popupShotHasPenaltySignal(shot.id);
    return true;
  }

  function selectedPopupImportMode() {
    const mode = $("popup-import-mode")?.value || "all";
    return ["all", "scored", "penalty"].includes(mode) ? mode : "all";
  }

  function importShotPopups() {
    const shots = orderedShotsByTime();
    if (shots.length === 0) {
      setStatus("No shots available to import into PopUp.");
      return;
    }
    const importMode = selectedPopupImportMode();
    const targetShots = shots.filter((shot) => popupShotMatchesImportMode(shot, importMode));
    if (targetShots.length === 0) {
      setStatus("No shots match the selected PopUp import mode.");
      return;
    }
    const targetShotIds = new Set(targetShots.map((shot) => shot.id));
    const preservedBubbles = popupBubbles().filter((bubble) => {
      if (bubble.anchor_mode !== "shot" || !bubble.shot_id) return true;
      return importMode !== "all" && !targetShotIds.has(bubble.shot_id);
    });
    const existingShotBubbleByShotId = new Map();
    const template = currentPopupTemplate();
    popupBubbles()
      .filter((bubble) => bubble.anchor_mode === "shot" && bubble.shot_id)
      .forEach((bubble) => {
        if (!existingShotBubbleByShotId.has(bubble.shot_id)) existingShotBubbleByShotId.set(bubble.shot_id, bubble);
      });
    const importedBubbles = targetShots.map((shot) => {
      const existingBubble = existingShotBubbleByShotId.get(shot.id);
      const defaultDurationMs = popupDefaultDurationMsForShot(shot, template);
      return normalizePopupBubble({
        ...(existingBubble || {}),
        id: existingBubble?.id || createPopupBubbleId(),
        text: popupTemplateTextForShot(shot),
        anchor_mode: "shot",
        shot_id: shot.id,
        time_ms: shot.time_ms,
        duration_ms: existingBubble?.duration_ms ?? defaultDurationMs,
        quadrant: existingBubble?.quadrant || "middle_middle",
        x: existingBubble?.x ?? 0.5,
        y: existingBubble?.y ?? 0.5,
        enabled: existingBubble?.enabled ?? template.enabled,
        width: existingBubble?.width ?? template.width,
        height: existingBubble?.height ?? template.height,
        follow_motion: existingBubble?.follow_motion ?? template.follow_motion,
        motion_mode: existingBubble?.motion_mode ?? template.motion_mode,
        content_type: existingBubble?.content_type || template.content_type,
        image_path: existingBubble?.image_path ?? template.image_path,
        image_scale_mode: existingBubble?.image_scale_mode ?? template.image_scale_mode,
        background_color: existingBubble?.background_color ?? template.background_color,
        text_color: existingBubble?.text_color ?? template.text_color,
        opacity: existingBubble?.opacity ?? template.opacity,
      });
    });
    setPopupBubbles([...preservedBubbles, ...importedBubbles], { commit: true, rerender: true });
    const focusShotId = selectedShotId() && targetShots.some((shot) => shot.id === selectedShotId()) ? selectedShotId() : targetShots[0]?.id || null;
    if (focusShotId) selectPopupBubbleForShot(focusShotId, { seek: true, reveal: true, focus: false, activateTool: true, expand: true });
  }

  function createPopupBubbleForShot(shotId) {
    if (!shotId) return false;
    const shot = orderedShotsByTime().find((item) => item.id === shotId) || null;
    if (!shot) {
      setStatus("Select a shot before creating a shot-linked marker.");
      return false;
    }
    const template = currentPopupTemplate();
    const defaultDurationMs = popupDefaultDurationMsForShot(shot, template);
    const nextBubble = normalizePopupBubble({
      id: createPopupBubbleId(),
      name: "",
      text: popupTemplateTextForShot(shot),
      anchor_mode: "shot",
      shot_id: shot.id,
      time_ms: shot.time_ms,
      duration_ms: defaultDurationMs,
      quadrant: "middle_middle",
      x: 0.5,
      y: 0.5,
      enabled: template.enabled,
      width: template.width,
      height: template.height,
      follow_motion: template.follow_motion,
      motion_mode: template.motion_mode,
      content_type: template.content_type,
      image_path: template.image_path,
      image_scale_mode: template.image_scale_mode,
      background_color: template.background_color,
      text_color: template.text_color,
      opacity: template.opacity,
    });
    setPopupBubbles([...popupBubbles(), nextBubble], { commit: true, rerender: true });
    selectPopupBubble(nextBubble.id, { seek: true, reveal: true, focus: false, activateTool: true, expand: false });
    return true;
  }

  function applyTemplateStyleToSelectedPopupBubble() {
    const bubble = selectedPopupBubble();
    if (!bubble) return false;
    const template = currentPopupTemplate();
    setPopupBubbles(popupBubbles().map((item) => item.id === bubble.id
      ? normalizePopupBubble({
          ...item,
          width: template.width,
          height: template.height,
          follow_motion: template.follow_motion,
          motion_mode: template.motion_mode,
          background_color: template.background_color,
          text_color: template.text_color,
          opacity: template.opacity,
        })
      : item), { commit: true, rerender: true });
    return true;
  }

  function popupBubbleFilterMatches(bubble, positionMs = currentPrimaryVideoPositionMs()) {
    if (!VALID_POPUP_FILTER_MODES.has(popupFilterMode())) setPopupFilterModeState("all");
    if (popupFilterMode() === "enabled") return Boolean(bubble.enabled);
    if (popupFilterMode() === "disabled") return !bubble.enabled;
    if (popupFilterMode() === "shot") return bubble.anchor_mode === "shot" && Boolean(bubble.shot_id);
    if (popupFilterMode() === "time") return bubble.anchor_mode !== "shot" || !bubble.shot_id;
    if (popupFilterMode() === "motion") return Boolean(bubble.follow_motion || popupBubbleMotionPath(bubble).length > 0);
    if (popupFilterMode() === "missing_text") return !popupBubbleResolvedText(bubble).trim();
    if (popupFilterMode() === "visible") return popupBubbleIsVisibleAtPosition(bubble, positionMs);
    return true;
  }

  function filteredPopupBubbles(bubbles = popupBubbles()) {
    const positionMs = currentPrimaryVideoPositionMs();
    return bubbles.filter((bubble) => popupBubbleFilterMatches(bubble, positionMs));
  }

  function sortedPopupBubblesForTimeline(bubbles = filteredPopupBubbles()) {
    return [...bubbles].sort((left, right) => {
      const timeDelta = popupBubbleEffectiveTimeMs(left) - popupBubbleEffectiveTimeMs(right);
      if (timeDelta !== 0) return timeDelta;
      return String(left.id || "").localeCompare(String(right.id || ""));
    });
  }

  function applySelectedPopupStyleToVisibleShotLinked() {
    const source = selectedPopupBubble();
    if (!source) return false;
    const visibleShotLinkedIds = new Set(
      filteredPopupBubbles(popupBubbles())
        .filter((bubble) => bubble.anchor_mode === "shot" && bubble.shot_id)
        .map((bubble) => bubble.id),
    );
    if (visibleShotLinkedIds.size === 0) return false;
    setPopupBubbles(popupBubbles().map((bubble) => visibleShotLinkedIds.has(bubble.id)
      ? normalizePopupBubble({
          ...bubble,
          width: source.width,
          height: source.height,
          background_color: source.background_color,
          text_color: source.text_color,
          opacity: source.opacity,
        })
      : bubble), { commit: true, rerender: true });
    return true;
  }

  function removePopupBubble(bubbleId) {
    const currentBubbles = popupBubbles();
    const removedIndex = currentBubbles.findIndex((bubble) => bubble.id === bubbleId);
    if (removedIndex < 0) return;
    popupGeneratedMotionOffsetsByBubbleId().delete(bubbleId);
    popupMotionGenerationSummaryByBubbleId().delete(bubbleId);
    const removingSelectedBubble = selectedPopupBubbleId() === bubbleId;
    const remainingBubbles = currentBubbles.filter((bubble) => bubble.id !== bubbleId);
    setPopupBubbles(remainingBubbles, { commit: true, rerender: true });
    if (!removingSelectedBubble) return;
    const fallbackBubble = remainingBubbles[removedIndex] || remainingBubbles[removedIndex - 1] || null;
    if (fallbackBubble) {
      selectPopupBubble(fallbackBubble.id, {
        seek: false,
        reveal: true,
        focus: false,
        activateTool: currentActiveTool() === "markers",
        expand: false,
      });
      return;
    }
    setSelectedPopupBubbleId(null);
    setSelectedPopupKeyframeOffset(0);
    render();
  }

  function duplicatePopupBubble(bubbleId) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return;
    const coordinates = popupBubblePoint(bubble);
    const motionPath = popupBubbleMotionPath(bubble).map((point) => ({
      offset_ms: point.offset_ms,
      x: clamp(point.x + 0.04, 0, 1),
      y: clamp(point.y + 0.04, 0, 1),
      easing: point.easing || "linear",
    }));
    setPopupBubbles([
      ...popupBubbles(),
      normalizePopupBubble({
        ...bubble,
        id: createPopupBubbleId(),
        quadrant: CUSTOM_QUADRANT_VALUE,
        x: clamp(coordinates.x + 0.04, 0, 1),
        y: clamp(coordinates.y + 0.04, 0, 1),
        motion_path: motionPath,
      }),
    ], { commit: true, rerender: true });
    const duplicate = popupBubbles()[popupBubbles().length - 1];
    if (duplicate) {
      copyPopupMotionUiState(bubble.id, [duplicate.id]);
      selectPopupBubble(duplicate.id, { seek: false, reveal: true, focus: true, activateTool: currentActiveTool() === "markers", expand: true });
    }
  }

  function clearPopupBubbleMotionPath(bubbleId) {
    setPopupMotionGeneratedOffsets(bubbleId, []);
    popupMotionGenerationSummaryByBubbleId().delete(bubbleId);
    if (selectedPopupBubbleId() === bubbleId) setSelectedPopupPlacementMode("base");
    setPopupBubbles(popupBubbles().map((bubble) => bubble.id === bubbleId
      ? normalizePopupBubble({ ...bubble, follow_motion: false, motion_path: [] })
      : bubble), { commit: true, rerender: true });
  }

  function seekPopupBubbleMotionPoint(bubbleId, offsetMs) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return false;
    return seekPrimaryVideoToTimeMs(popupBubbleEffectiveTimeMs(bubble) + Math.max(0, Math.round(Number(offsetMs) || 0)));
  }

  function setPopupBubbleMotionPointValue(bubbleId, offsetMs, field, rawValue, options = {}) {
    const normalizedOffset = Math.max(0, Math.round(Number(offsetMs) || 0));
    const nextBubbles = popupBubbles().map((bubble) => {
      if (bubble.id !== bubbleId) return bubble;
      const nextBubble = normalizePopupBubble(bubble);
      if (normalizedOffset <= 0) {
        if (field === "x" || field === "y") {
          const normalizedValue = normalizedCoordinateValue(rawValue);
          return normalizePopupBubble({
            ...nextBubble,
            quadrant: CUSTOM_QUADRANT_VALUE,
            [field]: normalizedValue === null ? nextBubble[field] : normalizedValue,
          });
        }
        return nextBubble;
      }
      const nextMotionPath = popupBubbleMotionPath(nextBubble).map((point) => {
        if (point.offset_ms !== normalizedOffset) return point;
        if (field === "offset_ms") {
          return {
            ...point,
            offset_ms: Math.max(1, Math.min(nextBubble.duration_ms, Math.round(Number(rawValue) || point.offset_ms))),
          };
        }
        if (field === "easing") {
          return {
            ...point,
            easing: popupKeyframeEasing(rawValue),
          };
        }
        const normalizedValue = normalizedCoordinateValue(rawValue);
        return {
          ...point,
          [field]: normalizedValue === null ? point[field] : normalizedValue,
        };
      });
      return normalizePopupBubble({
        ...nextBubble,
        follow_motion: true,
        motion_path: nextMotionPath,
      });
    });
    setPopupBubbles(nextBubbles, options);
  }

  function popupBubbleKeyframes(bubble) {
    const basePoint = popupBubblePoint(bubble);
    const motionPath = popupBubbleMotionPath(bubble);
    const keyframes = [
      { offset_ms: 0, x: basePoint.x, y: basePoint.y, easing: "linear", base: true },
      ...motionPath.map((point) => ({ ...point, base: false })),
    ];
    const finishOffsetMs = Math.max(1, Math.round(Number(bubble?.duration_ms ?? 1) || 1));
    if ((bubble?.follow_motion || motionPath.length > 0) && !keyframes.some((point) => point.offset_ms === finishOffsetMs)) {
      const finishPoint = popupBubbleMotionPointAtOffset(motionPath, finishOffsetMs, basePoint);
      keyframes.push({
        offset_ms: finishOffsetMs,
        x: finishPoint.x,
        y: finishPoint.y,
        easing: motionPath[motionPath.length - 1]?.easing || "linear",
        base: false,
        synthesized: true,
      });
    }
    return keyframes;
  }

  function popupMotionGuidePointRole(bubble, point) {
    if (!point || point.base || point.offset_ms <= 0) return "start";
    if (bubble && point.offset_ms >= Math.max(1, Math.round(Number(bubble.duration_ms ?? 1) || 1))) return "finish";
    return popupMotionOffsetIsGenerated(bubble?.id, point.offset_ms) ? "generated" : "detail";
  }

  function popupMotionGuideStepName(index, point = null, bubble = null) {
    const role = popupMotionGuidePointRole(bubble, point);
    if (role === "start") return "Start";
    if (role === "finish") return "Finish";
    return `Step ${Math.max(1, index)}`;
  }

  function popupMotionGuidePointName(point, index, bubble = null) {
    return popupMotionGuideStepName(index, point, bubble);
  }

  function popupMotionGuidePointLabel(point, index, bubble = null) {
    if (!point) return "";
    const role = popupMotionGuidePointRole(bubble, point);
    if (role === "start") return "@ 0.000s";
    if (role === "finish") return `Marker end @ ${precise(point.offset_ms)}s`;
    return `${role === "generated" ? "Auto" : "Detail"} @ ${precise(point.offset_ms)}s`;
  }

  function popupMotionGuideHintText(bubble, inBetweenCount) {
    const summary = popupMotionGenerationSummaryByBubbleId().get(bubble?.id);
    if (summary) return summary;
    if (inBetweenCount > 0) {
      return "Regenerate first tries to trace the video motion and falls back to evenly spaced in-between points. Add Detail splits the largest remaining time gap.";
    }
    return "Select Start or Finish below, then place it on the video. Generate first tries to trace the video motion and falls back to evenly spaced in-between points. Add Detail splits the largest remaining time gap.";
  }

  function selectedPopupMotionPoint(bubble) {
    if (!bubble) return { x: 0.5, y: 0.5, base: true, offset_ms: 0, easing: "linear" };
    const selectedOffset = selectedPopupPlacementMode() === "keyframe"
      ? selectedPopupKeyframeOffsetMs()
      : 0;
    return popupKeyframePoint(bubble, selectedOffset);
  }

  function popupKeyframePoint(bubble, offsetMs) {
    const normalizedOffset = Math.max(0, Math.round(Number(offsetMs) || 0));
    const keyframe = popupBubbleKeyframes(bubble).find((point) => point.offset_ms === normalizedOffset);
    if (keyframe) {
      return {
        x: keyframe.x,
        y: keyframe.y,
        base: Boolean(keyframe.base),
        offset_ms: keyframe.offset_ms,
        easing: popupKeyframeEasing(keyframe.easing),
        synthesized: Boolean(keyframe.synthesized),
      };
    }
    const fallbackPoint = popupBubblePoint(bubble, popupBubbleEffectiveTimeMs(bubble) + normalizedOffset);
    return {
      x: fallbackPoint.x,
      y: fallbackPoint.y,
      base: normalizedOffset <= 0,
      offset_ms: normalizedOffset,
      easing: "linear",
      synthesized: false,
    };
  }

  function popupMotionInBetweenOffsets(motionPath, finishOffsetMs) {
    return normalizePopupMotionPath(motionPath)
      .map((point) => Math.max(0, Math.round(Number(point.offset_ms) || 0)))
      .filter((offsetMs) => offsetMs > 0 && offsetMs < finishOffsetMs);
  }

  function popupMotionAlignPathToFinish(motionPath, finishOffsetMs, startPoint, finishPoint) {
    const normalizedPath = normalizePopupMotionPath(motionPath);
    if (normalizedPath.length === 0) return normalizedPath;
    const tracedFinishPoint = popupBubbleMotionPointAtOffset(normalizedPath, finishOffsetMs, startPoint);
    const deltaX = (finishPoint?.x ?? tracedFinishPoint.x) - tracedFinishPoint.x;
    const deltaY = (finishPoint?.y ?? tracedFinishPoint.y) - tracedFinishPoint.y;
    if (Math.abs(deltaX) < 0.0001 && Math.abs(deltaY) < 0.0001) return normalizedPath;
    return normalizePopupMotionPath(normalizedPath.map((point) => {
      const ratio = finishOffsetMs <= 0 ? 1 : clamp(point.offset_ms / finishOffsetMs, 0, 1);
      return {
        ...point,
        x: clamp(point.x + (deltaX * ratio), 0, 1),
        y: clamp(point.y + (deltaY * ratio), 0, 1),
      };
    }));
  }

  function generatePopupBubbleMotionPathLinear(bubbleId) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return false;
    const finishOffsetMs = Math.max(1, Math.round(Number(bubble.duration_ms ?? 1) || 1));
    const startPoint = popupKeyframePoint(bubble, 0);
    const finishPoint = popupKeyframePoint(bubble, finishOffsetMs);
    const { count, distancePx } = popupMotionSuggestedInBetweenCount(
      bubble,
      finishOffsetMs,
      startPoint,
      finishPoint,
    );
    const generatedOffsets = popupMotionAutoOffsets(finishOffsetMs, count);
    const nextMotionPath = [
      ...generatedOffsets.map((offsetMs) => {
        const point = popupMotionSamplePointForOffset(bubble, offsetMs, finishOffsetMs, startPoint, finishPoint);
        return {
          offset_ms: offsetMs,
          x: point.x,
          y: point.y,
          easing: "linear",
        };
      }),
      {
        offset_ms: finishOffsetMs,
        x: finishPoint.x,
        y: finishPoint.y,
        easing: popupKeyframeEasing(finishPoint.easing),
      },
    ];
    const nextBubble = normalizePopupBubble({
      ...bubble,
      follow_motion: true,
      motion_mode: "guided",
      motion_path: nextMotionPath,
    });
    const summary = count === 0
      ? `Auto kept just Start and Finish across ${precise(finishOffsetMs)}s and ${distancePx}px of travel.`
      : `Auto generated ${count} evenly spaced in-between point${count === 1 ? "" : "s"} across ${precise(finishOffsetMs)}s and ${distancePx}px of travel.`;
    setPopupMotionGeneratedOffsets(bubble.id, generatedOffsets);
    popupMotionGenerationSummaryByBubbleId().set(bubble.id, `${summary} Regenerate replaces the current in-between points.`);
    setPopupEditorSectionExpanded("motion", true);
    setSelectedPopupKeyframeOffset(generatedOffsets[0] ?? finishOffsetMs);
    setPopupBubbles(popupBubbles().map((item) => item.id === bubble.id ? nextBubble : item), { commit: true, rerender: true });
    setStatus(summary);
    return true;
  }

  function generatePopupBubbleMotionPath(bubbleId) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    const video = $("primary-video");
    if (!bubble) return false;
    if (getPopupAutoTraceBubbleId()) {
      setStatus("Finish the current motion trace before generating another path.");
      return false;
    }
    if (!(video instanceof HTMLVideoElement) || !currentState().media?.primary_available || Number(video.videoWidth || 0) <= 0) {
      return generatePopupBubbleMotionPathLinear(bubbleId);
    }
    const finishOffsetMs = Math.max(1, Math.round(Number(bubble.duration_ms ?? 1) || 1));
    const startPoint = popupKeyframePoint(bubble, 0);
    const finishPoint = popupKeyframePoint(bubble, finishOffsetMs);
    void autoTracePopupBubbleMotion(bubbleId)
      .then((traced) => {
        if (!traced) {
          generatePopupBubbleMotionPathLinear(bubbleId);
          return;
        }
        const tracedBubble = popupBubbles().find((item) => item.id === bubbleId);
        if (!tracedBubble) return;
        const tracedPath = popupBubbleMotionPath(tracedBubble);
        const alignedPath = popupMotionAlignPathToFinish(tracedPath, finishOffsetMs, startPoint, finishPoint);
        const generatedOffsets = popupMotionInBetweenOffsets(alignedPath, finishOffsetMs);
        const summary = generatedOffsets.length === 0
          ? `Generate traced Start and Finish from the video across ${precise(finishOffsetMs)}s.`
          : `Generate traced ${generatedOffsets.length} in-between point${generatedOffsets.length === 1 ? "" : "s"} from the video across ${precise(finishOffsetMs)}s.`;
        setPopupMotionGeneratedOffsets(bubbleId, generatedOffsets);
        popupMotionGenerationSummaryByBubbleId().set(bubbleId, `${summary} Regenerate replaces the current in-between points.`);
        setPopupEditorSectionExpanded("motion", true);
        setSelectedPopupKeyframeOffset(generatedOffsets[0] ?? finishOffsetMs);
        const pathChanged = JSON.stringify(alignedPath) !== JSON.stringify(tracedPath);
        if (pathChanged) {
          const nextBubble = normalizePopupBubble({
            ...tracedBubble,
            follow_motion: true,
            motion_mode: "guided",
            motion_path: alignedPath,
          });
          setPopupBubbles(popupBubbles().map((item) => item.id === bubbleId ? nextBubble : item), { commit: true, rerender: true });
        } else {
          renderPopupEditors();
          renderLiveOverlay();
        }
        setStatus(summary);
      })
      .catch(() => {
        generatePopupBubbleMotionPathLinear(bubbleId);
      });
    return true;
  }

  function syncSelectedPopupKeyframeOffset(bubble) {
    const keyframes = popupBubbleKeyframes(bubble);
    if (!keyframes.some((point) => point.offset_ms === selectedPopupKeyframeOffsetMs())) {
      setSelectedPopupKeyframeOffsetState(keyframes[keyframes.length - 1]?.offset_ms ?? 0);
    }
  }

  function setSelectedPopupKeyframeOffset(offsetMs) {
    const normalizedOffsetMs = Math.max(0, Math.round(Number(offsetMs) || 0));
    setSelectedPopupKeyframeOffsetState(normalizedOffsetMs);
    setSelectedPopupPlacementModeState(normalizedOffsetMs > 0 ? "keyframe" : "base");
  }

  function addPopupBubbleKeyframeAtPlayhead(bubbleId) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return false;
    const finishOffsetMs = Math.max(1, Math.round(Number(bubble.duration_ms ?? 1) || 1));
    if (finishOffsetMs <= 1) {
      setStatus("This marker is too short for an in-between detail step.");
      return false;
    }
    const offsetMs = popupMotionNextDetailOffsetMs(bubble);
    if (offsetMs === null) {
      setStatus("No room for another detail point between the existing motion points.");
      return false;
    }
    const startPoint = popupKeyframePoint(bubble, 0);
    const finishPoint = popupKeyframePoint(bubble, finishOffsetMs);
    const sampledPoint = popupMotionSamplePointForOffset(bubble, offsetMs, finishOffsetMs, startPoint, finishPoint);
    const nextMotionPath = normalizePopupMotionPath([
      ...popupBubbleMotionPath(bubble).filter((point) => point.offset_ms !== offsetMs),
      {
        offset_ms: offsetMs,
        x: sampledPoint.x,
        y: sampledPoint.y,
        easing: "linear",
      },
    ]);
    const nextBubble = normalizePopupBubble({
      ...bubble,
      follow_motion: true,
      motion_path: nextMotionPath,
    });
    setPopupEditorSectionExpanded("motion", true);
    setSelectedPopupKeyframeOffset(offsetMs);
    setPopupMotionGeneratedOffsets(bubble.id, [...popupGeneratedMotionOffsetsForBubbleId(bubble.id)].filter((value) => value !== offsetMs));
    setPopupBubbles(popupBubbles().map((item) => item.id === bubbleId ? nextBubble : item), { commit: true, rerender: true });
    seekPopupBubbleMotionPoint(bubbleId, offsetMs);
    return true;
  }

  function deletePopupBubbleKeyframe(bubbleId, offsetMs) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return false;
    const normalizedOffset = Math.max(0, Math.round(Number(offsetMs) || 0));
    if (normalizedOffset <= 0 || normalizedOffset >= Math.max(1, bubble.duration_ms)) return false;
    const nextBubbles = popupBubbles().map((item) => item.id === bubbleId
      ? normalizePopupBubble({
          ...item,
          motion_path: popupBubbleMotionPath(item).filter((point) => point.offset_ms !== normalizedOffset),
        })
      : item);
    setPopupMotionGeneratedOffsets(bubbleId, [...popupGeneratedMotionOffsetsForBubbleId(bubbleId)].filter((value) => value !== normalizedOffset));
    setSelectedPopupKeyframeOffset(0);
    setPopupBubbles(nextBubbles, { commit: true, rerender: true });
    return true;
  }

  function adjacentPopupKeyframeOffset(bubble, direction) {
    const keyframes = popupBubbleKeyframes(bubble);
    if (keyframes.length === 0) return 0;
    const currentIndex = keyframes.findIndex((point) => point.offset_ms === selectedPopupKeyframeOffsetMs());
    if (currentIndex < 0) return keyframes[0].offset_ms;
    const nextIndex = clamp(currentIndex + direction, 0, keyframes.length - 1);
    return keyframes[nextIndex].offset_ms;
  }

  function jumpPopupBubbleKeyframe(bubbleId, direction) {
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return false;
    syncSelectedPopupKeyframeOffset(bubble);
    const offsetMs = adjacentPopupKeyframeOffset(bubble, direction);
    setSelectedPopupKeyframeOffset(offsetMs);
    seekPopupBubbleMotionPoint(bubbleId, offsetMs);
    renderPopupEditors();
    return true;
  }

  function copyPopupBubbleMotionFromPrevious(bubbleId) {
    const ordered = sortedPopupBubblesForTimeline(popupBubbles());
    const index = ordered.findIndex((bubble) => bubble.id === bubbleId);
    if (index <= 0) return false;
    const source = ordered[index - 1];
    const target = ordered[index];
    const nextTarget = normalizePopupBubble({
      ...target,
      follow_motion: Boolean(source.follow_motion || popupBubbleMotionPath(source).length > 0),
      motion_path: popupBubbleMotionPath(source).map((point) => ({ ...point })),
    });
    setPopupEditorSectionExpanded("motion", true);
    setSelectedPopupKeyframeOffset(popupBubbleMotionPath(nextTarget)[0]?.offset_ms ?? 0);
    setPopupBubbles(popupBubbles().map((bubble) => bubble.id === bubbleId ? nextTarget : bubble), { commit: true, rerender: true });
    copyPopupMotionUiState(source.id, [bubbleId]);
    renderPopupEditors();
    return true;
  }

  function applyPopupBubbleMotionToVisibleShotLinked(bubbleId) {
    const source = popupBubbles().find((bubble) => bubble.id === bubbleId);
    if (!source) return false;
    const sourceMotion = popupBubbleMotionPath(source).map((point) => ({ ...point }));
    const targetIds = new Set(
      filteredPopupBubbles()
        .filter((bubble) => bubble.id !== bubbleId && bubble.anchor_mode === "shot" && bubble.shot_id)
        .map((bubble) => bubble.id),
    );
    if (targetIds.size === 0) {
      setStatus("No visible shot-linked popups to receive this motion path.");
      return false;
    }
    setPopupBubbles(popupBubbles().map((bubble) => targetIds.has(bubble.id)
      ? normalizePopupBubble({
          ...bubble,
          follow_motion: Boolean(source.follow_motion || sourceMotion.length > 0),
          motion_path: sourceMotion.map((point) => ({ ...point })),
        })
      : bubble), { commit: true, rerender: true });
    copyPopupMotionUiState(bubbleId, [...targetIds]);
    renderPopupEditors();
    setStatus(`Applied motion path to ${targetIds.size} shot-linked popup${targetIds.size === 1 ? "" : "s"}.`);
    return true;
  }

  function setPopupBubbleMotionUiMode(bubbleId, uiMode, options = {}) {
    const followMotion = uiMode !== "fixed";
    const motionMode = popupMotionModeValueForUiMode(uiMode);
    const nextBubbles = popupBubbles().map((bubble) => {
      if (bubble.id !== bubbleId) return bubble;
      return normalizePopupBubble({
        ...bubble,
        follow_motion: followMotion,
        motion_mode: motionMode,
      });
    });
    if (!followMotion) setSelectedPopupPlacementMode("base");
    if (followMotion) setPopupEditorSectionExpanded("motion", true);
    setPopupBubbles(nextBubbles, options);
  }

  function syncPopupBubbleMotionModeControls(card, bubble) {
    const uiMode = popupBubbleMotionUiMode(bubble);
    const toggle = card.querySelector('[data-popup-field="follow_motion"]');
    if (toggle instanceof HTMLInputElement) syncControlChecked(toggle, uiMode !== "fixed");
    card.querySelectorAll("[data-popup-motion-mode]").forEach((section) => {
      section.toggleAttribute("hidden", section.dataset.popupMotionMode !== uiMode);
    });
  }

  function setPopupAuthoringCollapsed(collapsed, { persistUiState = true, rerender = true } = {}) {
    setPopupAuthoringCollapsedValue(Boolean(collapsed));
    syncLocalProjectUiState();
    if (persistUiState) scheduleProjectUiStateApply();
    if (rerender) renderPopupEditors();
  }

  function beginPopupBubbleDrag(event) {
    if (event.button !== 0 || popupBubbleDrag() || !popupEditingActive()) return;
    const badge = event.target instanceof Element ? event.target.closest("[data-popup-drag]") : null;
    if (!(badge instanceof HTMLElement)) return;
    const bubbleId = badge.dataset.popupId || "";
    if (!bubbleId || bubbleId !== selectedPopupBubbleId()) return;
    const bubble = popupBubbles().find((item) => item.id === bubbleId);
    if (!bubble) return;
    const badgeRect = badge.getBoundingClientRect();
    const selectedMotionOffsetMs = Math.max(0, Math.round(Number(badge.dataset.popupMotionOffset) || 0));
    setSelectedPopupBubbleId(bubbleId);
    if (badge.dataset.popupMotionOffset !== undefined) {
      if (selectedMotionOffsetMs > 0) setSelectedPopupPlacementMode("keyframe", selectedMotionOffsetMs);
      else setSelectedPopupPlacementMode("base");
    } else {
      setSelectedPopupPlacementMode("base");
    }
    renderPopupEditors();
    renderLiveOverlay();
    const stage = $("video-stage");
    const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
    const currentPositionMs = overlayRenderPositionMs($("primary-video"));
    const renderPositionMs = popupBubbleRenderPositionMs(bubble, currentPositionMs);
    const renderedCoordinates = badge.dataset.popupMotionOffset !== undefined
      ? popupKeyframePoint(bubble, selectedMotionOffsetMs)
      : (resolveNormalizedPointFromRect(badgeRect, frameRect) || popupBubblePoint(bubble, renderPositionMs));
    const popupTimeMs = popupBubbleEffectiveTimeMs(bubble);
    const nextDrag = {
      bubbleId,
      target: $("popup-overlay"),
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: renderedCoordinates.x,
      startY: renderedCoordinates.y,
      motionOffsetMs: badge.dataset.popupMotionOffset !== undefined
        ? selectedMotionOffsetMs
        : Math.max(0, renderPositionMs - popupTimeMs),
      badgeWidth: Math.max(0, badgeRect.width || 0),
      badgeHeight: Math.max(0, badgeRect.height || 0),
      pointerOffsetX: clamp(event.clientX - badgeRect.left, 0, Math.max(0, badgeRect.width || 0)),
      pointerOffsetY: clamp(event.clientY - badgeRect.top, 0, Math.max(0, badgeRect.height || 0)),
      kind: badge.dataset.popupMotionOffset !== undefined && selectedMotionOffsetMs > 0 ? "keyframe" : "bubble",
    };
    setPopupBubbleDrag(nextDrag);
    setSelectedPopupKeyframeOffset(nextDrag.motionOffsetMs);
    capturePointer(nextDrag.target, event.pointerId);
    nextDrag.target?.classList.add("dragging");
    event.preventDefault();
    activity("popup.drag.start", { popup_id: bubbleId, x: renderedCoordinates.x, y: renderedCoordinates.y });
  }

  function movePopupBubbleDrag(event) {
    const drag = popupBubbleDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    const stage = $("video-stage");
    const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
    const width = Math.max(1, frameRect.width || 0);
    const height = Math.max(1, frameRect.height || 0);
    let newX;
    let newY;
    if (drag.kind === "bubble") {
      const badgeWidth = clamp(drag.badgeWidth || 0, 0, width);
      const badgeHeight = clamp(drag.badgeHeight || 0, 0, height);
      const pointerOffsetX = clamp(drag.pointerOffsetX ?? badgeWidth / 2, 0, badgeWidth);
      const pointerOffsetY = clamp(drag.pointerOffsetY ?? badgeHeight / 2, 0, badgeHeight);
      const nextLeft = clamp(event.clientX - frameRect.left - pointerOffsetX, 0, Math.max(0, width - badgeWidth));
      const nextTop = clamp(event.clientY - frameRect.top - pointerOffsetY, 0, Math.max(0, height - badgeHeight));
      newX = clamp((nextLeft + (badgeWidth / 2)) / width, 0, 1);
      newY = clamp((nextTop + (badgeHeight / 2)) / height, 0, 1);
    } else {
      const deltaX = (event.clientX - drag.startClientX) / width;
      const deltaY = (event.clientY - drag.startClientY) / height;
      newX = clamp(drag.startX + deltaX, 0, 1);
      newY = clamp(drag.startY + deltaY, 0, 1);
    }
    const nextBubbles = popupBubbles().map((bubble) => {
      if (bubble.id !== drag.bubbleId) return bubble;
      if (drag.kind === "keyframe" && drag.motionOffsetMs > 0) {
        const nextMotionPath = normalizePopupMotionPath([
          ...popupBubbleMotionPath(bubble).filter((point) => point.offset_ms !== drag.motionOffsetMs),
          {
            offset_ms: drag.motionOffsetMs,
            x: newX,
            y: newY,
            easing: popupKeyframePoint(bubble, drag.motionOffsetMs).easing || "linear",
          },
        ]);
        return normalizePopupBubble({
          ...bubble,
          follow_motion: true,
          motion_path: nextMotionPath,
        });
      }
      return normalizePopupBubble({ ...bubble, quadrant: CUSTOM_QUADRANT_VALUE, x: newX, y: newY });
    });
    setPopupBubbles(nextBubbles, { commit: false, rerender: false });
  }

  function endPopupBubbleDrag(event) {
    const drag = popupBubbleDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    releasePointer(drag.target, drag.pointerId ?? event.pointerId);
    drag.target?.classList.remove("dragging");
    setPopupBubbleDrag(null);
    renderPopupEditors();
    activity(drag.kind === "keyframe" ? "popup.keyframe.drag.commit" : "popup.drag.commit", {
      popup_id: drag.bubbleId,
      offset_ms: drag.motionOffsetMs,
    });
    callApi("/api/popups", { popups: popupBubbles() });
  }

  function visiblePopupBubbles(positionMs) {
    const editingActive = popupEditingActive();
    return popupBubbles().flatMap((bubble) => {
      const resolvedText = popupBubbleResolvedText(bubble).trim();
      const hasImage = ["image", "text_image"].includes(bubble.content_type) && Boolean(String(bubble.image_path || "").trim());
      const hasText = ["text", "text_image"].includes(bubble.content_type) && Boolean(resolvedText);
      if (!bubble.enabled || (!hasImage && !hasText)) return [];
      const isVisible = popupBubbleIsVisibleAtPosition(bubble, positionMs);
      const isSelectedEditorBubble = editingActive && bubble.id === selectedPopupBubbleId();
      if (!isVisible && !isSelectedEditorBubble) return [];
      if (editingActive && !isSelectedEditorBubble) return [];
      return [{
        bubble,
        text: resolvedText,
        hasImage,
        hasText,
        positionMs: isVisible ? positionMs : popupBubbleRenderPositionMs(bubble, positionMs),
        selected: isSelectedEditorBubble,
        outsideWindow: !isVisible,
      }];
    });
  }

  function popupOverlayPixelPoint(frameRect, xValue, yValue) {
    const x = clamp(Number(xValue) || 0, 0, 1);
    const y = clamp(Number(yValue) || 0, 0, 1);
    return {
      left: clamp(x * frameRect.width, 0, frameRect.width),
      top: clamp(y * frameRect.height, 0, frameRect.height),
    };
  }

  function renderPopupKeyframeOverlay(popupOverlay, bubble, frameRect) {
    if (popupBubbleMotionUiMode(bubble) === "fixed") return;
    const keyframes = popupBubbleKeyframes(bubble);
    if (keyframes.length === 0) return;
    if (popupEditingActive()) return;
    const entries = keyframes.map((point) => ({
      ...point,
      pixel: popupOverlayPixelPoint(frameRect, point.x, point.y),
    }));
    entries.forEach((point, index) => {
      if (index === 0) return;
      const previous = entries[index - 1];
      const deltaX = point.pixel.left - previous.pixel.left;
      const deltaY = point.pixel.top - previous.pixel.top;
      const segment = documentObject.createElement("div");
      segment.className = "popup-keyframe-path";
      if (!bubble.follow_motion) segment.classList.add("paused");
      segment.style.left = `${previous.pixel.left}px`;
      segment.style.top = `${previous.pixel.top}px`;
      segment.style.width = `${Math.max(1, Math.hypot(deltaX, deltaY))}px`;
      segment.style.transform = `translateY(-50%) rotate(${Math.atan2(deltaY, deltaX)}rad)`;
      popupOverlay.appendChild(segment);
    });
    entries.forEach((point, index) => {
      const handle = documentObject.createElement("button");
      handle.type = "button";
      handle.className = "popup-keyframe-dot";
      if (point.base) handle.classList.add("base");
      if (!bubble.follow_motion) handle.classList.add("paused");
      if (point.offset_ms === selectedPopupKeyframeOffsetMs()) handle.classList.add("selected");
      handle.dataset.popupKeyframeDrag = point.base || bubble.follow_motion ? "true" : "false";
      handle.dataset.popupId = bubble.id;
      handle.dataset.popupKeyframeOffset = String(point.offset_ms);
      handle.title = point.base
        ? "Base point"
        : `${popupMotionGuidePointLabel(point, index, bubble)} (${popupKeyframeEasing(point.easing).replace(/_/g, " ")})`;
      handle.style.left = `${point.pixel.left}px`;
      handle.style.top = `${point.pixel.top}px`;
      handle.addEventListener("click", (clickEvent) => {
        clickEvent.preventDefault();
        clickEvent.stopPropagation();
        setSelectedPopupBubbleId(bubble.id);
        setSelectedPopupKeyframeOffset(point.offset_ms);
        seekPopupBubbleMotionPoint(bubble.id, point.offset_ms);
        renderPopupEditors();
        renderLiveOverlay();
      });
      popupOverlay.appendChild(handle);
    });
  }

  function renderPopupOverlay(popupOverlay, frameRect, overlayScale, _size, positionMs) {
    if (!popupOverlay) return;
    if (!($("show-markers")?.checked ?? true)) {
      popupOverlay.hidden = true;
      popupOverlay.innerHTML = "";
      return;
    }
    popupOverlay.hidden = false;
    popupOverlay.innerHTML = "";
    popupOverlay.style.left = `${frameRect.left}px`;
    popupOverlay.style.top = `${frameRect.top}px`;
    popupOverlay.style.width = `${frameRect.width}px`;
    popupOverlay.style.height = `${frameRect.height}px`;
    const editingActive = popupEditingActive();
    visiblePopupBubbles(positionMs).forEach((entry) => {
      const bubble = entry.bubble;
      const selectorStyle = editingActive && entry.selected
        ? popupBubblePlacementSelectorStyle(bubble)
        : null;
      const basePoint = popupKeyframePoint(bubble, 0);
      const point = selectorStyle ? basePoint : popupBubblePoint(bubble, entry.positionMs);
      const popupStyle = popupBubbleRenderStyle(bubble);
      const popupSize = selectorStyle
        ? { width: selectorStyle.width, height: selectorStyle.height }
        : resolvedPopupBubbleSize(bubble);
      const scaledWidth = Math.max(1, scaledOverlayPixelValue(popupSize.width, overlayScale, 1));
      const scaledHeight = Math.max(1, scaledOverlayPixelValue(popupSize.height, overlayScale, 1));
      const scaledGap = selectorStyle ? 0 : scaledOverlayPixelValue(6, overlayScale, 2);
      const scaledPaddingY = selectorStyle ? 0 : scaledOverlayPixelValue(8, overlayScale, 2);
      const scaledPaddingX = selectorStyle ? 0 : scaledOverlayPixelValue(10, overlayScale, 2);
      const selectorHasText = Boolean(selectorStyle?.show_text);
      const selectorToken = selectorHasText ? String(selectorStyle?.token || "") : "";
      const selectorTokenLength = selectorHasText ? Math.max(1, selectorToken.length || 1) : 1;
      const selectorFontSize = clamp(
        Math.round(Math.min(scaledWidth, scaledHeight) * (selectorTokenLength >= 3 ? 0.28 : selectorTokenLength === 2 ? 0.33 : 0.42)),
        scaledOverlayPixelValue(8, overlayScale, 8),
        scaledOverlayPixelValue(selectorTokenLength >= 3 ? 10 : 12, overlayScale, selectorTokenLength >= 3 ? 10 : 12),
      );
      const scaledFontSize = selectorStyle
        ? selectorFontSize
        : scaledOverlayPixelValue(currentState().project?.overlay?.font_size || 14, overlayScale, 1);
      const badge = documentObject.createElement("div");
      badge.className = "overlay-badge popup-overlay-badge";
      badge.classList.toggle("popup-placement-selector", Boolean(selectorStyle));
      badge.style.minWidth = `${scaledWidth}px`;
      badge.style.minHeight = `${scaledHeight}px`;
      badge.style.width = `${scaledWidth}px`;
      badge.style.height = `${scaledHeight}px`;
      badge.style.backgroundColor = rgba(selectorStyle ? selectorStyle.background_color : popupStyle.background_color, selectorStyle ? 0.96 : bubble.opacity);
      badge.style.color = selectorStyle ? selectorStyle.text_color : popupStyle.text_color;
      badge.style.border = "0";
      badge.style.borderRadius = selectorStyle ? "999px" : "0";
      badge.style.boxShadow = "none";
      badge.style.display = "flex";
      badge.style.flexDirection = "column";
      badge.style.alignItems = "center";
      badge.style.justifyContent = "center";
      badge.style.gap = `${scaledGap}px`;
      badge.style.padding = `${scaledPaddingY}px ${scaledPaddingX}px`;
      badge.style.boxSizing = "border-box";
      badge.style.fontSize = `${scaledFontSize}px`;
      badge.style.textAlign = "center";
      if (entry.hasImage && !selectorStyle) {
        const image = documentObject.createElement("img");
        image.src = popupBubbleImageUrl(bubble);
        image.alt = "";
        image.style.width = "100%";
        image.style.height = entry.hasText ? `calc(100% - ${Math.max(18, scaledOverlayPixelValue(28, overlayScale, 18))}px)` : "100%";
        image.style.objectFit = bubble.image_scale_mode === "cover" ? "cover" : "contain";
        image.style.pointerEvents = "none";
        badge.appendChild(image);
      }
      if (entry.hasText && (!selectorStyle || selectorHasText)) {
        const text = documentObject.createElement("div");
        text.textContent = selectorToken || entry.text;
        text.style.alignItems = "center";
        text.style.display = "flex";
        text.style.flex = "1 1 auto";
        text.style.fontWeight = selectorStyle ? selectorStyle.font_weight : popupStyle.font_weight;
        text.style.fontVariantNumeric = selectorStyle ? "tabular-nums" : "normal";
        text.style.height = "100%";
        text.style.justifyContent = "center";
        text.style.letterSpacing = selectorStyle ? (selectorTokenLength >= 3 ? "-0.05em" : selectorTokenLength === 2 ? "-0.03em" : "0") : "0";
        text.style.lineHeight = "1";
        text.style.pointerEvents = "none";
        text.style.textShadow = "none";
        text.style.textAlign = "center";
        text.style.whiteSpace = "nowrap";
        text.style.width = "100%";
        badge.appendChild(text);
      }
      const allowDrag = editingActive && entry.selected;
      if (allowDrag) badge.dataset.popupDrag = "true";
      else delete badge.dataset.popupDrag;
      badge.dataset.popupId = bubble.id;
      if (selectorStyle) badge.dataset.popupMotionOffset = "0";
      else delete badge.dataset.popupMotionOffset;
      badge.classList.toggle("popup-selected", Boolean(entry.selected));
      badge.classList.toggle("popup-outside-window", Boolean(entry.outsideWindow));
      placeOverlayBadge(popupOverlay, badge, frameRect, point.x, point.y);
    });
  }

  function setMarkersExpanded(expanded, { persistUiState = true } = {}) {
    const root = $("cockpit-root");
    const nextExpanded = Boolean(expanded);
    const markersActive = currentActiveTool() === "markers";
    const wasExpanded = Boolean(root?.classList.contains("markers-expanded"));
    if (nextExpanded && markersActive && !wasExpanded) capturePopupWorkbenchRestoreState();
    if (nextExpanded && markersActive) cancelOverlayDragInteractions("markers.editing");
    root?.classList.toggle("markers-expanded", nextExpanded && markersActive);
    if (nextExpanded) root?.classList.remove("waveform-expanded", "timing-expanded", "metrics-expanded", "scoring-expanded");
    const section = $("markers-workbench");
    if (section instanceof HTMLElement) section.hidden = !(nextExpanded && markersActive);
    activity("markers.expand", { expanded: nextExpanded });
    syncLocalProjectUiState();
    if (persistUiState) scheduleProjectUiStateApply();
    renderPopupEditors();
    if (nextExpanded) {
      renderLiveOverlay();
      return;
    }
    scheduleReviewStageRestore();
  }

  return Object.freeze({
    selectPopupBubble,
    selectPopupBubbleForShot,
    selectedPopupBubble,
    setSelectedPopupPlacementMode,
    popupPlacementSummary,
    setPopupBubbles,
    syncPopupBubbleSizeControls,
    setPopupBubbleField,
    currentPrimaryVideoPositionMs,
    addPopupBubble,
    popupShotMatchesImportMode,
    selectedPopupImportMode,
    importShotPopups,
    createPopupBubbleForShot,
    applyTemplateStyleToSelectedPopupBubble,
    popupBubbleFilterMatches,
    filteredPopupBubbles,
    sortedPopupBubblesForTimeline,
    applySelectedPopupStyleToVisibleShotLinked,
    removePopupBubble,
    duplicatePopupBubble,
    clearPopupBubbleMotionPath,
    seekPopupBubbleMotionPoint,
    setPopupBubbleMotionPointValue,
    popupBubbleKeyframes,
    popupMotionGuidePointRole,
    popupMotionGuideStepName,
    popupMotionGuidePointName,
    popupMotionGuidePointLabel,
    popupMotionGuideHintText,
    selectedPopupMotionPoint,
    popupKeyframePoint,
    popupMotionInBetweenOffsets,
    popupMotionAlignPathToFinish,
    generatePopupBubbleMotionPathLinear,
    generatePopupBubbleMotionPath,
    syncSelectedPopupKeyframeOffset,
    setSelectedPopupKeyframeOffset,
    addPopupBubbleKeyframeAtPlayhead,
    deletePopupBubbleKeyframe,
    jumpPopupBubbleKeyframe,
    copyPopupBubbleMotionFromPrevious,
    applyPopupBubbleMotionToVisibleShotLinked,
    setPopupBubbleMotionUiMode,
    syncPopupBubbleMotionModeControls,
    setPopupAuthoringCollapsed,
    beginPopupBubbleDrag,
    movePopupBubbleDrag,
    endPopupBubbleDrag,
    visiblePopupBubbles,
    renderPopupKeyframeOverlay,
    renderPopupOverlay,
    setMarkersExpanded,
  });
}
