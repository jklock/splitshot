export function createOverlayPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  getOverlayStyleMode = () => "square",
  setOverlayStyleMode = () => {},
  getOverlaySpacing = () => 8,
  setOverlaySpacing = () => {},
  getOverlayMargin = () => 8,
  setOverlayMargin = () => {},
  getOverlayVisibilityPosition = () => "bottom",
  setOverlayVisibilityPosition = () => {},
  getOverlayColorCommitTimer = () => null,
  setOverlayColorCommitTimer = () => {},
  getOverlayBadgeDrag = () => null,
  setOverlayBadgeDrag = () => {},
  getTextBoxDrag = () => null,
  setTextBoxDrag = () => {},
  getCustomOverlayRenderKey = () => "",
  setCustomOverlayRenderKey = () => {},
  getTextBoxRenderedPositionById = () => new Map(),
  setTextBoxRenderedPositionById = () => {},
  normalizedCoordinateValue = (value) => value,
  normalizeOverlayTextBox = (box) => box,
  overlayTextBoxes = () => [],
  preferredLegacyTextBox = (boxes) => boxes[0] || null,
  syncLegacyOverlayBoxState = () => {},
  setLocalOverlayTextBoxes = () => {},
  overlayTextBoxDisplayText = (box) => box?.text || "",
  overlayTextBoxLabel = (_box, index) => `Text Box ${index + 1}`,
  resolvedOverlayTextBoxSize = () => ({ width: 0, height: 0 }),
  syncOverlayBubbleSizeControls = () => {},
  syncControlValue = () => {},
  clamp = (value, min, max) => Math.min(max, Math.max(min, value)),
  clampNumber = (value, min, max) => Math.min(max, Math.max(min, value)),
  isColorInput = () => false,
  readColorControlValue = () => "#000000",
  setColorControlValue = () => {},
  overlayHexControlFor = () => null,
  syncOverlayHexControl = () => {},
  openColorPicker = () => {},
  updateColorFromHexInput = () => {},
  opacityValueFromPercent = (value) => value,
  validOverlayBadgeNames = new Set(),
  overlayStackLockControls = {},
  badgeFontSizes = { M: 14 },
  customQuadrantValue = "custom",
  aboveFinalTextBoxValue = "above_final",
  overlayColorCommitDelayMs = 900,
  usesCustomQuadrant = (value) => value === customQuadrantValue,
  scheduleInteractionPreviewRender = () => {},
  scheduleOverlayApply = () => {},
  previewFrameClientRect = () => null,
  resolveNormalizedPointFromRect = () => null,
  roundedRect = (rect) => rect,
  positionOverlayContainer = () => {},
  pinCustomOverlayAnchor = () => {},
  placeOverlayBadge = () => false,
  previewFrameGeometry = () => null,
  overlayDisplayScale = () => 1,
  overlayAutoBubbleSize = () => ({ width: 0, height: 0 }),
  textBiasForDirection = () => "center",
  currentShotIndex = () => -1,
  overlayRenderPositionMs = () => 0,
  orderedShotsByTime = () => [],
  shotDisplayTimeMs = (value) => value,
  resolvedSplitMsForShot = () => null,
  splitRowIntervalLabel = () => "",
  shotBadgeBaseText = () => "",
  scoreBadgeContent = () => "",
  splitSeconds = (value) => String(value ?? ""),
  seconds = (value) => String(value ?? ""),
  badgeElement = () => document.createElement("span"),
  scaledOverlayPixelValue = (value) => Number(value) || 0,
  alignToEdge = (value) => value,
  renderPopupOverlay = () => {},
  popupEditingActive = () => false,
  capturePointer = () => {},
  releasePointer = () => {},
  activity = () => {},
  callApi = async () => null,
  cancelAutoApplyOverlay = () => {},
  renderTextBoxEditors = () => {},
  flushInteractionPreviewRender = () => {},
  queueInspectorScrollRestore = () => {},
  flushDeferredRender = () => {},
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function previewFrameRectForOverlayPlacement() {
    const stage = $("video-stage");
    if (!stage) return null;
    return previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
  }

  function previewFrameRectForTextBoxes() {
    const stage = $("video-stage");
    if (!stage) return null;
    return previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
  }

  function overlayBadgeElement(kind) {
    if (kind === "shots") {
      const overlay = $("live-overlay");
      return overlay?.querySelector('[data-overlay-drag="shots"]') || overlay?.firstElementChild || null;
    }
    return [...documentObject.querySelectorAll(`[data-overlay-drag="${kind}"]`)].find(
      (element) => element instanceof HTMLElement,
    ) || null;
  }

  function overlayBadgeCoordinateFallback(kind) {
    if (kind === "shots") {
      const fallbackX = normalizedCoordinateValue($("overlay-custom-x")?.value);
      const fallbackY = normalizedCoordinateValue($("overlay-custom-y")?.value);
      if (fallbackX === null || fallbackY === null) return null;
      return { x: fallbackX, y: fallbackY };
    }
    const config = overlayStackLockControls[kind];
    if (!config) return null;
    const fallbackX = normalizedCoordinateValue($(config.xId)?.value ?? currentState()?.project?.overlay?.[`${kind}_x`]);
    const fallbackY = normalizedCoordinateValue($(config.yId)?.value ?? currentState()?.project?.overlay?.[`${kind}_y`]);
    if (fallbackX === null || fallbackY === null) return null;
    return { x: fallbackX, y: fallbackY };
  }

  function overlayDragConfiguration(kind) {
    return {
      timer: { lockId: "timer-lock-to-stack", xId: "timer-x", yId: "timer-y" },
      draw: { lockId: "draw-lock-to-stack", xId: "draw-x", yId: "draw-y" },
      score: { lockId: "score-lock-to-stack", xId: "score-x", yId: "score-y" },
      shots: {
        xId: "overlay-custom-x",
        yId: "overlay-custom-y",
        quadrantId: "shot-quadrant",
        quadrantValue: customQuadrantValue,
      },
    }[kind] || null;
  }

  function overlayDragAnchor(kind, badge, frameRect) {
    if (kind === "shots") {
      const overlay = $("live-overlay");
      const anchorBadge = overlay?.firstElementChild;
      const anchorRect = anchorBadge?.getBoundingClientRect() || overlay?.getBoundingClientRect() || badge.getBoundingClientRect();
      return {
        x: clamp((anchorRect.left - frameRect.left + (anchorRect.width / 2)) / Math.max(1, frameRect.width), 0, 1),
        y: clamp((anchorRect.top - frameRect.top + (anchorRect.height / 2)) / Math.max(1, frameRect.height), 0, 1),
      };
    }
    const rect = badge.getBoundingClientRect();
    return {
      x: clamp((rect.left - frameRect.left + (rect.width / 2)) / Math.max(1, frameRect.width), 0, 1),
      y: clamp((rect.top - frameRect.top + (rect.height / 2)) / Math.max(1, frameRect.height), 0, 1),
    };
  }

  function positionTextBoxBadge(badge, box, frameRect, { anchorBadge = null, anchorRect = null, scale = 1 } = {}) {
    if (box.quadrant === aboveFinalTextBoxValue) {
      const resolvedAnchorRect = anchorRect || (anchorBadge instanceof HTMLElement ? anchorBadge.getBoundingClientRect() : null);
      if (!resolvedAnchorRect) return false;
      const badgeRect = badge.getBoundingClientRect();
      const gap = scaledOverlayPixelValue(getOverlaySpacing(), scale, 0);
      const halfWidth = Math.max(0, badgeRect.width / 2);
      const centerX = clamp(
        (resolvedAnchorRect.left - frameRect.left) + (resolvedAnchorRect.width / 2),
        halfWidth,
        Math.max(halfWidth, frameRect.width - halfWidth),
      );
      const top = clamp(
        (resolvedAnchorRect.top - frameRect.top) - gap,
        Math.max(0, badgeRect.height),
        Math.max(0, frameRect.height),
      );
      badge.style.position = "absolute";
      badge.style.margin = "0";
      badge.style.left = `${centerX}px`;
      badge.style.top = `${top}px`;
      badge.style.transform = "translate(-50%, -100%)";
      return true;
    }
    const customX = normalizedCoordinateValue(box.x);
    const customY = normalizedCoordinateValue(box.y);
    if (customX === null || customY === null) return false;
    badge.style.position = "absolute";
    badge.style.margin = "0";
    badge.style.left = `${clamp(customX * frameRect.width, 0, frameRect.width)}px`;
    badge.style.top = `${clamp(customY * frameRect.height, 0, frameRect.height)}px`;
    badge.style.transform = "translate(-50%, -50%)";
    return true;
  }

  function configureTextBoxGroup(group, quadrant, _frameRect, scale = 1) {
    const [vertical = "top", horizontal = "left"] = String(quadrant || "top_left").split("_");
    const horizontalLayout = vertical === "middle";
    group.classList.remove("horizontal", "vertical");
    group.classList.add(horizontalLayout ? "horizontal" : "vertical");
    group.style.justifyContent = alignToEdge(vertical);
    group.style.alignItems = alignToEdge(horizontal);
    const scaledGap = scaledOverlayPixelValue(getOverlaySpacing(), scale, 0);
    const scaledMargin = scaledOverlayPixelValue(getOverlayMargin(), scale, 0);
    group.style.padding = `${scaledMargin}px`;
    group.style.gap = `${scaledGap}px`;
    group.style.left = "0px";
    group.style.top = "0px";
    group.style.width = "100%";
    group.style.height = "100%";
  }

  function readOverlayPayload() {
    const styles = {};
    documentObject.querySelectorAll(".style-card[data-badge]").forEach((card) => {
      const badge = card.dataset.badge || "";
      if (!validOverlayBadgeNames.has(badge)) return;
      styles[badge] = {};
      card.querySelectorAll("[data-field]").forEach((input) => {
        const value = isColorInput(input)
          ? readColorControlValue(input)
          : input.dataset.field === "opacity"
            ? opacityValueFromPercent(input.value)
            : input.type === "range"
              ? Number(input.value)
              : input.value;
        styles[badge][input.dataset.field] = value;
      });
    });
    const scoringColors = {};
    documentObject.querySelectorAll(".score-color-input").forEach((input) => {
      scoringColors[input.dataset.letter] = readColorControlValue(input);
    });
    const textBoxes = overlayTextBoxes().map((box, index) => normalizeOverlayTextBox(box, index));
    const primaryTextBox = preferredLegacyTextBox(textBoxes);
    const showOverlay = $("show-overlay")?.checked ?? true;
    const position = showOverlay ? (getOverlayVisibilityPosition() || currentState()?.settings?.overlay_position || "bottom") : "none";
    if (showOverlay && position !== "none") setOverlayVisibilityPosition(position);
    return {
      position,
      badge_size: $("badge-size").value,
      styles,
      scoring_colors: scoringColors,
      style_type: getOverlayStyleMode(),
      spacing: getOverlaySpacing(),
      margin: getOverlayMargin(),
      max_visible_shots: Number($("max-visible-shots").value || 4),
      shot_quadrant: $("shot-quadrant").value,
      shot_direction: $("shot-direction").value,
      custom_x: $("overlay-custom-x").value,
      custom_y: $("overlay-custom-y").value,
      timer_x: $("timer-x").value,
      timer_y: $("timer-y").value,
      draw_x: $("draw-x").value,
      draw_y: $("draw-y").value,
      score_x: $("score-x").value,
      score_y: $("score-y").value,
      bubble_width: Number($("bubble-width").value || 0),
      bubble_height: Number($("bubble-height").value || 0),
      font_family: $("overlay-font-family").value,
      font_size: Number($("overlay-font-size").value || badgeFontSizes[$("badge-size").value] || 14),
      font_bold: $("overlay-font-bold").checked,
      font_italic: $("overlay-font-italic").checked,
      show_timer: $("show-timer").checked,
      show_draw: $("show-draw").checked,
      show_shots: $("show-shots").checked,
      show_shot_scores: $("show-shot-scores").checked,
      show_score: $("show-score").checked,
      timer_lock_to_stack: $("timer-lock-to-stack").checked,
      draw_lock_to_stack: $("draw-lock-to-stack").checked,
      score_lock_to_stack: $("score-lock-to-stack").checked,
      text_boxes: textBoxes.map((box) => ({
        id: box.id,
        enabled: box.enabled,
        lock_to_stack: box.lock_to_stack,
        source: box.source,
        text: box.text,
        quadrant: box.quadrant,
        x: box.x,
        y: box.y,
        background_color: box.background_color,
        text_color: box.text_color,
        opacity: box.opacity,
        width: box.width,
        height: box.height,
        summary_metric_ids: Array.isArray(box.summary_metric_ids) ? box.summary_metric_ids.slice() : [],
        style_type: box.style_type,
        font_family: box.font_family,
        font_size: box.font_size,
        font_bold: box.font_bold,
        font_italic: box.font_italic,
      })),
      custom_box_enabled: Boolean(primaryTextBox?.enabled),
      custom_box_mode: primaryTextBox?.source || "manual",
      custom_box_text: primaryTextBox?.text || "",
      custom_box_quadrant: primaryTextBox?.quadrant || "top_right",
      custom_box_x: primaryTextBox?.x ?? "",
      custom_box_y: primaryTextBox?.y ?? "",
      custom_box_background_color: primaryTextBox?.background_color || "#000000",
      custom_box_text_color: primaryTextBox?.text_color || "#ffffff",
      custom_box_opacity: Number(primaryTextBox?.opacity ?? 0.9),
      custom_box_width: Number(primaryTextBox?.width || 0),
      custom_box_height: Number(primaryTextBox?.height || 0),
    };
  }

  function syncOverlayPreviewStateFromControls() {
    if (!currentState()?.project) return;
    const payload = readOverlayPayload();
    const overlay = currentState().project.overlay;
    overlay.position = payload.position;
    overlay.badge_size = payload.badge_size;
    overlay.style_type = payload.style_type;
    overlay.spacing = Math.max(0, Number(payload.spacing || 0));
    overlay.margin = Math.max(0, Number(payload.margin || 0));
    overlay.max_visible_shots = Math.max(1, Number(payload.max_visible_shots || overlay.max_visible_shots || 1));
    overlay.shot_quadrant = payload.shot_quadrant;
    overlay.shot_direction = payload.shot_direction;
    overlay.custom_x = normalizedCoordinateValue(payload.custom_x);
    overlay.custom_y = normalizedCoordinateValue(payload.custom_y);
    overlay.timer_x = normalizedCoordinateValue(payload.timer_x);
    overlay.timer_y = normalizedCoordinateValue(payload.timer_y);
    overlay.draw_x = normalizedCoordinateValue(payload.draw_x);
    overlay.draw_y = normalizedCoordinateValue(payload.draw_y);
    overlay.score_x = normalizedCoordinateValue(payload.score_x);
    overlay.score_y = normalizedCoordinateValue(payload.score_y);
    overlay.bubble_width = Math.max(0, Number(payload.bubble_width || 0));
    overlay.bubble_height = Math.max(0, Number(payload.bubble_height || 0));
    overlay.font_family = payload.font_family;
    overlay.font_size = Math.max(8, Number(payload.font_size || overlay.font_size || 14));
    overlay.font_bold = Boolean(payload.font_bold);
    overlay.font_italic = Boolean(payload.font_italic);
    overlay.show_timer = Boolean(payload.show_timer);
    overlay.show_draw = Boolean(payload.show_draw);
    overlay.show_shots = Boolean(payload.show_shots);
    overlay.show_shot_scores = Boolean(payload.show_shot_scores);
    overlay.show_score = Boolean(payload.show_score);
    overlay.timer_lock_to_stack = Boolean(payload.timer_lock_to_stack);
    overlay.draw_lock_to_stack = Boolean(payload.draw_lock_to_stack);
    overlay.score_lock_to_stack = Boolean(payload.score_lock_to_stack);
    const previousTextBoxes = Array.isArray(overlay.text_boxes) ? overlay.text_boxes : [];
    const payloadTextBoxes = Array.isArray(payload.text_boxes) ? payload.text_boxes : [];
    const preserveExistingTextBoxes = Boolean(
      payloadTextBoxes.length === 0
        && previousTextBoxes.length > 0,
    );
    overlay.text_boxes = (preserveExistingTextBoxes ? previousTextBoxes : payloadTextBoxes)
      .map((box, index) => normalizeOverlayTextBox(box, index));
    syncLegacyOverlayBoxState(overlay, overlay.text_boxes);
    Object.entries(payload.styles).forEach(([badgeName, style]) => {
      const badge = overlay[badgeName];
      if (!badge) return;
      if (style.background_color) badge.background_color = style.background_color;
      if (style.text_color) badge.text_color = style.text_color;
      if (style.opacity !== undefined) badge.opacity = clamp(Number(style.opacity), 0, 1);
    });
    overlay.scoring_colors = {
      ...overlay.scoring_colors,
      ...payload.scoring_colors,
    };
    setOverlayStyleMode(overlay.style_type || getOverlayStyleMode());
    setOverlaySpacing(Number(overlay.spacing ?? getOverlaySpacing()));
    setOverlayMargin(Number(overlay.margin ?? getOverlayMargin()));
    syncOverlayBubbleSizeControls();
  }

  function previewOverlayControlChanges() {
    syncOverlayPreviewStateFromControls();
    scheduleInteractionPreviewRender({ overlay: true });
  }

  function commitOverlayControlChanges() {
    previewOverlayControlChanges();
    scheduleOverlayApply();
  }

  function clearOverlayColorCommitTimer() {
    if (getOverlayColorCommitTimer() === null) return;
    windowObject.clearTimeout(getOverlayColorCommitTimer());
    setOverlayColorCommitTimer(null);
  }

  function scheduleOverlayColorCommit() {
    clearOverlayColorCommitTimer();
    setOverlayColorCommitTimer(windowObject.setTimeout(() => {
      setOverlayColorCommitTimer(null);
      scheduleOverlayApply();
    }, overlayColorCommitDelayMs));
  }

  function flushOverlayColorCommit() {
    if (getOverlayColorCommitTimer() === null) return;
    clearOverlayColorCommitTimer();
    scheduleOverlayApply();
  }

  function bindOverlayColorInput(control) {
    if (!isColorInput(control) || control.dataset.overlayColorBound === "true") return;
    control.dataset.overlayColorBound = "true";
    const hexInput = overlayHexControlFor(control);
    setColorControlValue(control, readColorControlValue(control));
    syncOverlayHexControl(control);
    control.addEventListener("click", () => openColorPicker(control));
    control.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      openColorPicker(control);
    });
    if (hexInput instanceof HTMLInputElement && hexInput.dataset.overlayColorBound !== "true") {
      hexInput.dataset.overlayColorBound = "true";
      syncOverlayHexControl(control);
      hexInput.addEventListener("input", () => updateColorFromHexInput(hexInput));
      hexInput.addEventListener("change", () => updateColorFromHexInput(hexInput, { commit: true }));
      hexInput.addEventListener("blur", () => updateColorFromHexInput(hexInput, { commit: true }));
    }
  }

  function syncOverlayCoordinateControlState() {
    const customEnabled = usesCustomQuadrant($("shot-quadrant").value);
    [["overlay-custom-x", "X"], ["overlay-custom-y", "Y"]].forEach(([id, axis]) => {
      const input = $(id);
      input.disabled = !customEnabled;
      input.placeholder = customEnabled ? "0.50" : "Custom only";
      input.title = customEnabled
        ? `Set custom ${axis.toLowerCase()} position from 0 to 1.`
        : "Enable the Custom quadrant to edit coordinates.";
    });
  }

  function resolveRenderedOverlayBadgeCoordinates(kind) {
    const frameRect = previewFrameRectForOverlayPlacement();
    const badge = overlayBadgeElement(kind);
    if (frameRect && badge instanceof HTMLElement) {
      return kind === "shots"
        ? overlayDragAnchor(kind, badge, frameRect)
        : resolveNormalizedPointFromRect(badge.getBoundingClientRect(), frameRect);
    }
    return overlayBadgeCoordinateFallback(kind);
  }

  function resetOverlayPlacementBaseline(controlId) {
    if (controlId === "shot-quadrant") {
      if (usesCustomQuadrant($("shot-quadrant").value)) {
        const coords = resolveRenderedOverlayBadgeCoordinates("shots") || { x: 0.5, y: 0.5 };
        syncControlValue($("overlay-custom-x"), coords.x);
        syncControlValue($("overlay-custom-y"), coords.y);
        return;
      }
      syncControlValue($("overlay-custom-x"), "");
      syncControlValue($("overlay-custom-y"), "");
      return;
    }

    const entry = Object.entries(overlayStackLockControls).find(([_kind, config]) => config.lockId === controlId);
    if (!entry) return;
    const [kind, config] = entry;
    const coords = resolveRenderedOverlayBadgeCoordinates(kind);
    if (!coords) return;
    syncControlValue($(config.xId), coords.x);
    syncControlValue($(config.yId), coords.y);
  }

  function syncOverlayBadgeCoordinateControlValues() {
    Object.entries(overlayStackLockControls).forEach(([kind, config]) => {
      if (!$(config.lockId)?.checked) return;
      const coords = resolveRenderedOverlayBadgeCoordinates(kind);
      if (!coords) return;
      if ($(config.xId)?.disabled) syncControlValue($(config.xId), coords.x);
      if ($(config.yId)?.disabled) syncControlValue($(config.yId), coords.y);
    });
  }

  function overlayBadgeLockedToStack(kind, overlay = currentState()?.project?.overlay) {
    if (!overlay || !(kind in overlayStackLockControls)) return false;
    return Boolean(overlay[`${kind}_lock_to_stack`] ?? true);
  }

  function syncOverlayBubbleLockControlState() {
    Object.values(overlayStackLockControls).forEach(({ lockId, xId, yId, label }) => {
      const lockControl = $(lockId);
      const isLocked = Boolean(lockControl?.checked);
      [[xId, "X"], [yId, "Y"]].forEach(([id, axis]) => {
        const input = $(id);
        if (!input) return;
        input.disabled = isLocked;
        input.placeholder = isLocked ? "Stack locked" : "auto";
        input.title = isLocked
          ? `${label} follows the shot stack while locked.`
          : `${label} ${axis} uses a normalized coordinate from 0 to 1. Leave it blank to follow the stack.`;
      });
    });
  }

  function overlayTextBoxBadge(boxId) {
    const customOverlay = $("custom-overlay");
    if (!customOverlay) return null;
    return [...customOverlay.querySelectorAll("[data-text-box-id]")].find(
      (element) => element instanceof HTMLElement && element.dataset.textBoxId === boxId,
    ) || null;
  }

  function resolveRenderedTextBoxCoordinates(boxId, fallbackBox = null) {
    const frameRect = previewFrameRectForTextBoxes();
    const badge = overlayTextBoxBadge(boxId);
    const liveCoordinates = frameRect && badge instanceof HTMLElement
      ? resolveNormalizedPointFromRect(badge.getBoundingClientRect(), frameRect)
      : null;
    if (liveCoordinates) return liveCoordinates;
    const cachedCoordinates = getTextBoxRenderedPositionById().get(boxId) || null;
    if (cachedCoordinates) return cachedCoordinates;
    if (!fallbackBox) return null;
    const fallbackX = normalizedCoordinateValue(fallbackBox.x);
    const fallbackY = normalizedCoordinateValue(fallbackBox.y);
    if (fallbackX === null || fallbackY === null) return null;
    return { x: fallbackX, y: fallbackY };
  }

  function unlockedOverlayTextBox(box, coordinates = null) {
    const nextCoordinates = coordinates
      || resolveRenderedTextBoxCoordinates(box.id, box)
      || {
        x: normalizedCoordinateValue(box.x) ?? 0.5,
        y: normalizedCoordinateValue(box.y) ?? 0.5,
      };
    return normalizeOverlayTextBox({
      ...box,
      lock_to_stack: false,
      quadrant: customQuadrantValue,
      x: nextCoordinates.x,
      y: nextCoordinates.y,
    });
  }

  function syncLockedTextBoxEditorCoordinates() {
    overlayTextBoxes().forEach((box) => {
      if (!box.lock_to_stack || box.quadrant === aboveFinalTextBoxValue) return;
      const coordinates = resolveRenderedTextBoxCoordinates(box.id, box);
      if (!coordinates) return;
      const card = [...documentObject.querySelectorAll(".text-box-card[data-box-id]")].find(
        (element) => element instanceof HTMLElement && element.dataset.boxId === box.id,
      );
      if (!(card instanceof HTMLElement)) return;
      const xInput = card.querySelector('[data-text-box-field="x"]');
      const yInput = card.querySelector('[data-text-box-field="y"]');
      if (xInput instanceof HTMLInputElement && xInput.disabled) syncControlValue(xInput, coordinates.x);
      if (yInput instanceof HTMLInputElement && yInput.disabled) syncControlValue(yInput, coordinates.y);
    });
  }

  function visibleOverlayTextBoxEntries(finalShotReached) {
    return overlayTextBoxes()
      .map((box, index) => {
        const textValue = overlayTextBoxDisplayText(box).trim();
        if (!box.enabled || !textValue || (box.source === "imported_summary" && !finalShotReached)) return null;
        return { box, index, textValue };
      })
      .filter(Boolean);
  }

  function overlayTextBoxStyle(box) {
    return {
      background_color: box.background_color || currentState().project.overlay.hit_factor_badge.background_color,
      text_color: box.text_color || currentState().project.overlay.hit_factor_badge.text_color,
      opacity: box.opacity ?? currentState().project.overlay.hit_factor_badge.opacity,
    };
  }

  function overlayStackBadges(overlay) {
    if (!(overlay instanceof HTMLElement)) return [];
    return [...overlay.querySelectorAll(".overlay-badge")].filter(
      (element) => element instanceof HTMLElement && !element.dataset.textBoxId,
    );
  }

  function overlayStackAnchorRect(overlay) {
    const candidates = overlayStackBadges(overlay);
    if (candidates.length === 0) return null;
    let left = Number.POSITIVE_INFINITY;
    let top = Number.POSITIVE_INFINITY;
    let right = Number.NEGATIVE_INFINITY;
    let bottom = Number.NEGATIVE_INFINITY;
    candidates.forEach((element) => {
      const rect = element.getBoundingClientRect();
      if (!Number.isFinite(rect.width) || !Number.isFinite(rect.height) || rect.width <= 0 || rect.height <= 0) return;
      left = Math.min(left, rect.left);
      top = Math.min(top, rect.top);
      right = Math.max(right, rect.right);
      bottom = Math.max(bottom, rect.bottom);
    });
    if (![left, top, right, bottom].every(Number.isFinite)) return null;
    return {
      left,
      top,
      width: Math.max(0, right - left),
      height: Math.max(0, bottom - top),
    };
  }

  function overlayStackTerminalRect(overlay) {
    const badges = overlayStackBadges(overlay);
    if (badges.length === 0) return null;
    const direction = currentState()?.project?.overlay?.shot_direction || "right";
    const terminalBadge = badges.reduce((selected, candidate) => {
      if (!(selected instanceof HTMLElement)) return candidate;
      const selectedRect = selected.getBoundingClientRect();
      const candidateRect = candidate.getBoundingClientRect();
      if (direction === "left") return candidateRect.left < selectedRect.left ? candidate : selected;
      if (direction === "up") return candidateRect.top < selectedRect.top ? candidate : selected;
      if (direction === "down") return candidateRect.bottom > selectedRect.bottom ? candidate : selected;
      return candidateRect.right > selectedRect.right ? candidate : selected;
    }, badges[0]);
    return terminalBadge instanceof HTMLElement ? terminalBadge.getBoundingClientRect() : null;
  }

  function customOverlayKey(entries, frameRect, overlayScale, finalScoreBadge, stackAnchorRect = null) {
    const overlayState = currentState()?.project?.overlay || {};
    const finalScoreRect = finalScoreBadge?.getBoundingClientRect();
    const stackTerminalRect = overlayStackTerminalRect($("live-overlay"));
    return JSON.stringify({
      frame: roundedRect(frameRect),
      scale: Math.round(overlayScale * 1000) / 1000,
      spacing: getOverlaySpacing(),
      margin: getOverlayMargin(),
      style_type: getOverlayStyleMode(),
      badge_size: overlayState.badge_size,
      bubble_width: overlayState.bubble_width,
      bubble_height: overlayState.bubble_height,
      font_family: overlayState.font_family,
      font_size: overlayState.font_size,
      font_bold: overlayState.font_bold,
      font_italic: overlayState.font_italic,
      final_score: roundedRect(finalScoreRect),
      stack_anchor: roundedRect(stackAnchorRect),
      stack_terminal: roundedRect(stackTerminalRect),
      entries: entries.map(({ box, textValue }) => ({
        id: box.id,
        lock_to_stack: box.lock_to_stack,
        source: box.source,
        text: textValue,
        quadrant: box.quadrant,
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        background_color: box.background_color,
        text_color: box.text_color,
        opacity: box.opacity,
      })),
    });
  }

  function firstStackLockedTextBoxRect(badgeRect, frameRect, scale = 1) {
    const quadrant = currentState()?.project?.overlay?.shot_quadrant || "bottom_left";
    const [vertical = "bottom", horizontal = "left"] = String(quadrant).split("_");
    const scaledMargin = scaledOverlayPixelValue(getOverlayMargin(), scale, 0);
    const left = horizontal === "left"
      ? scaledMargin
      : horizontal === "middle"
        ? Math.max(0, (frameRect.width - badgeRect.width) / 2)
        : Math.max(0, frameRect.width - badgeRect.width - scaledMargin);
    const top = vertical === "top"
      ? scaledMargin
      : vertical === "middle"
        ? Math.max(0, (frameRect.height - badgeRect.height) / 2)
        : Math.max(0, frameRect.height - badgeRect.height - scaledMargin);
    return {
      left,
      top,
      width: badgeRect.width,
      height: badgeRect.height,
    };
  }

  function nextStackLockedTextBoxRect(baseRect, badgeRect, frameRect, scale = 1) {
    const direction = currentState()?.project?.overlay?.shot_direction || "right";
    const gap = scaledOverlayPixelValue(getOverlaySpacing(), scale, 0);
    let left = baseRect.left;
    let top = baseRect.top;
    if (direction === "left") {
      left = baseRect.left - badgeRect.width - gap;
      top = baseRect.top + (baseRect.height / 2) - (badgeRect.height / 2);
    } else if (direction === "up") {
      left = baseRect.left + (baseRect.width / 2) - (badgeRect.width / 2);
      top = baseRect.top - badgeRect.height - gap;
    } else if (direction === "down") {
      left = baseRect.left + (baseRect.width / 2) - (badgeRect.width / 2);
      top = baseRect.top + baseRect.height + gap;
    } else {
      left = baseRect.left + baseRect.width + gap;
      top = baseRect.top + (baseRect.height / 2) - (badgeRect.height / 2);
    }
    return {
      left: clamp(left, 0, Math.max(0, frameRect.width - badgeRect.width)),
      top: clamp(top, 0, Math.max(0, frameRect.height - badgeRect.height)),
      width: badgeRect.width,
      height: badgeRect.height,
    };
  }

  function positionStackLockedTextBoxBadge(badge, frameRect, { terminalRect = null, previousRect = null, scale = 1 } = {}) {
    const badgeRect = badge.getBoundingClientRect();
    const baseRect = previousRect || (terminalRect
      ? {
          left: terminalRect.left - frameRect.left,
          top: terminalRect.top - frameRect.top,
          width: terminalRect.width,
          height: terminalRect.height,
        }
      : null);
    const nextRect = baseRect
      ? nextStackLockedTextBoxRect(baseRect, badgeRect, frameRect, scale)
      : firstStackLockedTextBoxRect(badgeRect, frameRect, scale);
    badge.style.position = "absolute";
    badge.style.margin = "0";
    badge.style.left = `${nextRect.left}px`;
    badge.style.top = `${nextRect.top}px`;
    badge.style.transform = "";
    return nextRect;
  }

  function renderCustomOverlayBoxes(customOverlay, entries, frameRect, overlayScale, size, finalScoreBadge, stackAnchorRect = null, terminalRect = null) {
    customOverlay.innerHTML = "";
    const textBoxGroups = new Map();
    const nextRenderedPositions = new Map();
    let stackLockedPreviousRect = null;
    entries.forEach(({ box, index, textValue }) => {
      const resolvedSize = resolvedOverlayTextBoxSize(box);
      const customBadge = badgeElement(
        textValue,
        overlayTextBoxStyle(box),
        size,
        null,
        resolvedSize.width,
        resolvedSize.height,
        "center",
        overlayScale,
      );
      customBadge.style.borderRadius = box.style_type === "pill"
        ? "999px"
        : box.style_type === "rounded" ? "16px" : "0";
      customBadge.style.fontFamily = String(box.font_family || "Arial");
      customBadge.style.fontSize = `${Math.max(8, Number(box.font_size || 14)) * overlayScale}px`;
      customBadge.style.fontWeight = box.font_bold ? "700" : "400";
      customBadge.style.fontStyle = box.font_italic ? "italic" : "normal";
      customBadge.dataset.textBoxDrag = "true";
      customBadge.dataset.textBoxId = box.id;
      customBadge.dataset.textBoxLabel = overlayTextBoxLabel(box, index);
      customBadge.dataset.textBoxSource = box.source || "manual";
      customOverlay.appendChild(customBadge);
      if (box.lock_to_stack && box.quadrant !== aboveFinalTextBoxValue) {
        stackLockedPreviousRect = positionStackLockedTextBoxBadge(customBadge, frameRect, {
          terminalRect,
          previousRect: stackLockedPreviousRect,
          scale: overlayScale,
        });
        const coordinates = resolveNormalizedPointFromRect(customBadge.getBoundingClientRect(), frameRect);
        if (coordinates) nextRenderedPositions.set(box.id, coordinates);
        return;
      }
      const aboveFinalAnchorRect = box.quadrant === aboveFinalTextBoxValue
        ? (!(finalScoreBadge instanceof HTMLElement) && box.source === "imported_summary" ? stackAnchorRect : null)
        : stackAnchorRect;
      if (positionTextBoxBadge(customBadge, box, frameRect, {
        anchorBadge: box.quadrant === aboveFinalTextBoxValue ? finalScoreBadge : null,
        anchorRect: aboveFinalAnchorRect,
        scale: overlayScale,
      })) {
        const coordinates = resolveNormalizedPointFromRect(customBadge.getBoundingClientRect(), frameRect);
        if (coordinates) nextRenderedPositions.set(box.id, coordinates);
        return;
      }
      customBadge.remove();
      const quadrant = box.quadrant === aboveFinalTextBoxValue
        ? "top_middle"
        : (box.quadrant || "top_right");
      let group = textBoxGroups.get(quadrant);
      if (!group) {
        group = documentObject.createElement("div");
        group.className = "text-box-group";
        configureTextBoxGroup(group, quadrant, frameRect, overlayScale);
        textBoxGroups.set(quadrant, group);
        customOverlay.appendChild(group);
      }
      group.appendChild(customBadge);
      const coordinates = resolveNormalizedPointFromRect(customBadge.getBoundingClientRect(), frameRect);
      if (coordinates) nextRenderedPositions.set(box.id, coordinates);
    });
    setTextBoxRenderedPositionById(nextRenderedPositions);
    customOverlay.classList.toggle("has-badge", customOverlay.childElementCount > 0);
  }

  function beginTextBoxDrag(event) {
    if (popupEditingActive()) return;
    if (getTextBoxDrag() || getOverlayBadgeDrag()) return;
    const customOverlay = $("custom-overlay");
    const customBadge = event.target instanceof Element
      ? event.target.closest("[data-text-box-drag]")
      : null;
    const renderedBoxId = customBadge?.dataset?.textBoxId || "";
    let box = overlayTextBoxes().find((item) => item.id === renderedBoxId);
    if (!box && customBadge?.dataset?.textBoxSource) {
      box = overlayTextBoxes().find((item) => item.source === customBadge.dataset.textBoxSource);
    }
    const boxId = box?.id || renderedBoxId;
    if (
      event.button !== 0
      || !customOverlay
      || !customOverlay.classList.contains("has-badge")
      || !box
      || !overlayTextBoxDisplayText(box).trim()
      || !(customBadge instanceof HTMLElement)
      || !customOverlay.contains(customBadge)
    ) return;
    event.preventDefault();
    const stage = $("video-stage");
    const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
    const badgeRect = customBadge.getBoundingClientRect();
    if (box.lock_to_stack && box.quadrant !== aboveFinalTextBoxValue) {
      const anchor = overlayDragAnchor("shots", customBadge, frameRect);
      setOverlayBadgeDrag({
        target: stage,
        kind: "shots",
        sourceKind: "text_box",
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        startX: anchor.x,
        startY: anchor.y,
        preservedTextBoxes: overlayTextBoxes(),
      });
      capturePointer(stage, event.pointerId);
      stage.classList.add("overlay-dragging");
      activity("overlay.drag.start", { kind: "shots", source_kind: "text_box", x: anchor.x, y: anchor.y });
      return;
    }
    const startX = clamp((badgeRect.left - frameRect.left + badgeRect.width / 2) / frameRect.width, 0, 1);
    const startY = clamp((badgeRect.top - frameRect.top + badgeRect.height / 2) / frameRect.height, 0, 1);
    setTextBoxDrag({
      boxId,
      target: customOverlay,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX,
      startY,
    });
    capturePointer(customOverlay, event.pointerId);
    customOverlay.classList.add("dragging");
    activity("overlay.text_box.drag.start", { box_id: boxId, x: startX, y: startY });
  }

  function moveTextBoxDrag(event) {
    const drag = getTextBoxDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    const stage = $("video-stage");
    if (!stage) return;
    const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
    const width = Math.max(1, frameRect.width || 0);
    const height = Math.max(1, frameRect.height || 0);
    const { startClientX, startClientY, startX, startY } = drag;
    const deltaX = (event.clientX - startClientX) / width;
    const deltaY = (event.clientY - startClientY) / height;
    const newX = clamp(startX + deltaX, 0, 1);
    const newY = clamp(startY + deltaY, 0, 1);
    const boxes = overlayTextBoxes().map((box) => box.id === drag.boxId
      ? normalizeOverlayTextBox({ ...box, quadrant: customQuadrantValue, x: newX, y: newY })
      : box);
    setLocalOverlayTextBoxes(boxes);
    syncOverlayPreviewStateFromControls();
    scheduleInteractionPreviewRender({ overlay: true });
  }

  function endTextBoxDrag(event) {
    const drag = getTextBoxDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    const customOverlay = $("custom-overlay");
    releasePointer(drag.target || customOverlay, drag.pointerId ?? event.pointerId);
    customOverlay?.classList.remove("dragging");
    const box = overlayTextBoxes().find((item) => item.id === drag.boxId);
    activity("overlay.text_box.drag.commit", {
      box_id: drag.boxId,
      x: box?.x ?? null,
      y: box?.y ?? null,
    });
    cancelAutoApplyOverlay();
    setTextBoxDrag(null);
    renderTextBoxEditors();
    flushInteractionPreviewRender();
    queueInspectorScrollRestore();
    callApi("/api/overlay", readOverlayPayload());
    flushDeferredRender();
  }

  function beginOverlayBadgeDrag(event) {
    if (popupEditingActive()) return;
    if (event.button !== 0 || getOverlayBadgeDrag()) return;
    const badge = event.target instanceof Element ? event.target.closest("[data-overlay-drag]") : null;
    if (!(badge instanceof HTMLElement)) return;
    const kind = badge.dataset.overlayDrag || "";
    const initialConfig = overlayDragConfiguration(kind);
    const effectiveKind = initialConfig?.lockId && $(initialConfig.lockId)?.checked ? "shots" : kind;
    const config = overlayDragConfiguration(effectiveKind);
    if (!config || !currentState()?.project) return;
    const stage = $("video-stage");
    const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
    const anchor = overlayDragAnchor(effectiveKind, badge, frameRect);
    setOverlayBadgeDrag({
      target: stage,
      kind: effectiveKind,
      sourceKind: kind,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: anchor.x,
      startY: anchor.y,
      preservedTextBoxes: overlayTextBoxes(),
    });
    capturePointer(stage, event.pointerId);
    stage.classList.add("overlay-dragging");
    event.preventDefault();
    activity("overlay.drag.start", { kind: effectiveKind, source_kind: kind, x: anchor.x, y: anchor.y });
  }

  function moveOverlayBadgeDrag(event) {
    const drag = getOverlayBadgeDrag();
    if (!drag || !currentState()?.project) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    const config = overlayDragConfiguration(drag.kind);
    if (!config) return;
    const stage = $("video-stage");
    const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
    const width = Math.max(1, frameRect.width || 0);
    const height = Math.max(1, frameRect.height || 0);
    const deltaX = (event.clientX - drag.startClientX) / width;
    const deltaY = (event.clientY - drag.startClientY) / height;
    const nextX = clamp(drag.startX + deltaX, 0, 1);
    const nextY = clamp(drag.startY + deltaY, 0, 1);
    const overlay = currentState().project.overlay;

    if (config.quadrantId) {
      $(config.quadrantId).value = config.quadrantValue;
      overlay.shot_quadrant = config.quadrantValue;
      syncOverlayCoordinateControlState();
    }
    const xControl = $(config.xId);
    const yControl = $(config.yId);
    const nextXValue = nextX.toFixed(3);
    const nextYValue = nextY.toFixed(3);
    xControl.value = nextXValue;
    yControl.value = nextYValue;
    if (config.xId === "overlay-custom-x") overlay.custom_x = nextX;
    if (config.yId === "overlay-custom-y") overlay.custom_y = nextY;
    if (config.xId === "timer-x") overlay.timer_x = nextX;
    if (config.yId === "timer-y") overlay.timer_y = nextY;
    if (config.xId === "draw-x") overlay.draw_x = nextX;
    if (config.yId === "draw-y") overlay.draw_y = nextY;
    if (config.xId === "score-x") overlay.score_x = nextX;
    if (config.yId === "score-y") overlay.score_y = nextY;
    scheduleInteractionPreviewRender({ overlay: true });
  }

  function endOverlayBadgeDrag(event) {
    const drag = getOverlayBadgeDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    const config = overlayDragConfiguration(drag.kind);
    releasePointer(drag.target, drag.pointerId ?? event.pointerId);
    drag.target.classList.remove("overlay-dragging");
    setOverlayBadgeDrag(null);
    if (
      Array.isArray(drag.preservedTextBoxes)
      && drag.preservedTextBoxes.length > 0
      && overlayTextBoxes().length === 0
    ) {
      setLocalOverlayTextBoxes(drag.preservedTextBoxes);
    }
    flushInteractionPreviewRender();
    if (config) {
      activity("overlay.drag.commit", {
        kind: drag.kind,
        x: normalizedCoordinateValue($(config.xId)?.value),
        y: normalizedCoordinateValue($(config.yId)?.value),
      });
      scheduleOverlayApply();
    }
    flushDeferredRender();
  }

  function renderLiveOverlay(positionMsOverride = null) {
    if (!currentState()?.project) return;
    const overlay = $("live-overlay");
    const customOverlay = $("custom-overlay");
    const popupOverlay = $("popup-overlay");
    const scoreLayer = $("score-layer");
    const position = currentState().project.overlay.position;
    const textBoxDragging = customOverlay.classList.contains("dragging");
    overlay.className = `live-overlay overlay-${position}`;
    customOverlay.className = `live-overlay overlay-${position}`;
    if (textBoxDragging) customOverlay.classList.add("dragging");
    overlay.innerHTML = "";
    scoreLayer.innerHTML = "";
    if (!currentState().media.primary_available) {
      if (popupOverlay) popupOverlay.innerHTML = "";
      customOverlay.innerHTML = "";
      customOverlay.classList.remove("has-badge");
      setCustomOverlayRenderKey("");
      return;
    }
    const stage = $("video-stage");
    const video = $("primary-video");
    const frameGeometry = previewFrameGeometry(video, stage);
    const frameRect = roundedRect(frameGeometry?.frameRect || stage.getBoundingClientRect());
    const frameClientRect = roundedRect(previewFrameClientRect(video, stage) || stage.getBoundingClientRect());
    const overlayScale = frameGeometry?.scale || overlayDisplayScale(video, frameRect);
    const positionMs = Number.isFinite(positionMsOverride)
      ? Math.max(0, Math.floor(positionMsOverride))
      : overlayRenderPositionMs(video);
    renderPopupOverlay(popupOverlay, frameRect, overlayScale, currentState().project.overlay.badge_size, positionMs);
    if (position === "none") {
      customOverlay.innerHTML = "";
      customOverlay.classList.remove("has-badge");
      setCustomOverlayRenderKey("");
      return;
    }
    positionOverlayContainer(overlay, currentState().project.overlay.shot_quadrant, frameRect, {
      x: currentState().project.overlay.custom_x,
      y: currentState().project.overlay.custom_y,
    }, overlayScale);
    customOverlay.style.left = `${frameRect.left}px`;
    customOverlay.style.top = `${frameRect.top}px`;
    customOverlay.style.width = `${frameRect.width}px`;
    customOverlay.style.height = `${frameRect.height}px`;
    customOverlay.style.transform = "";
    customOverlay.style.justifyContent = "flex-start";
    customOverlay.style.alignItems = "flex-start";
    customOverlay.style.padding = "0";
    customOverlay.style.gap = "0";
    scoreLayer.style.left = `${frameRect.left}px`;
    scoreLayer.style.top = `${frameRect.top}px`;
    scoreLayer.style.width = `${frameRect.width}px`;
    scoreLayer.style.height = `${frameRect.height}px`;

    const beep = currentState().project.analysis.beep_time_ms_primary;
    let elapsed = beep === null || beep === undefined ? positionMs : Math.max(0, positionMs - beep);
    const shots = orderedShotsByTime();
    const firstShotTime = shots.length > 0 ? shotDisplayTimeMs(shots[0].time_ms) : null;
    const finalShotIndex = shots.length - 1;
    const finalShotTime = finalShotIndex >= 0 ? shotDisplayTimeMs(shots[finalShotIndex].time_ms) : null;
    const finalShotReached = finalShotTime !== null && finalShotTime !== undefined && positionMs >= finalShotTime;
    if (beep !== null && beep !== undefined && shots.length > 0) {
      const lastShotMs = shots[shots.length - 1].time_ms;
      elapsed = Math.min(elapsed, Math.max(0, lastShotMs - beep));
    }
    const size = currentState().project.overlay.badge_size;
    const shotTextBias = textBiasForDirection(currentState().project.overlay.shot_direction || "right");
    const autoBubbleSize = currentState().project.overlay.bubble_width > 0 && currentState().project.overlay.bubble_height > 0
      ? null
      : overlayAutoBubbleSize();
    const activeShotIndex = currentShotIndex(positionMs);
    const splitRowsByShotId = new Map((currentState().split_rows || []).filter((row) => row.shot_id).map((row) => [row.shot_id, row]));
    const appendOverlayBadge = (badge, kind = "", xValue = null, yValue = null) => {
      if (!overlayBadgeLockedToStack(kind) && placeOverlayBadge(scoreLayer, badge, frameRect, xValue, yValue)) {
        return;
      }
      if (kind === "" && placeOverlayBadge(scoreLayer, badge, frameRect, xValue, yValue)) {
        return;
      }
      if (kind === "shots") {
        overlay.appendChild(badge);
        return;
      }
      overlay.appendChild(badge);
    };
    if (currentState().project.overlay.show_timer) {
      const timerBadge = badgeElement(`Timer ${seconds(elapsed)}`, currentState().project.overlay.timer_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);
      timerBadge.dataset.overlayDrag = "timer";
      appendOverlayBadge(timerBadge, "timer", currentState().project.overlay.timer_x, currentState().project.overlay.timer_y);
    }
    if (
      currentState().project.overlay.show_draw
      && firstShotTime !== null
      && (beep === null || beep === undefined || positionMs >= beep)
      && positionMs < firstShotTime
      && currentState().metrics.draw_ms !== null
      && currentState().metrics.draw_ms !== undefined
      && Number(currentState().metrics.draw_ms) > 0
    ) {
      const drawBadge = badgeElement(`Draw ${seconds(currentState().metrics.draw_ms)}`, currentState().project.overlay.shot_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);
      drawBadge.dataset.overlayDrag = "draw";
      appendOverlayBadge(drawBadge, "draw", currentState().project.overlay.draw_x, currentState().project.overlay.draw_y);
    }

    if (currentState().project.overlay.show_shots && activeShotIndex >= 0) {
      const maxVisible = Math.max(1, Number(currentState().project.overlay.max_visible_shots || 4));
      const start = Math.max(0, activeShotIndex - maxVisible + 1);
      for (let index = start; index <= activeShotIndex; index += 1) {
        const shot = shots[index];
        if (!shot) continue;
        const splitRow = splitRowsByShotId.get(shot.id) || null;
        const splitMs = resolvedSplitMsForShot(shot.id, index + 1, shot.time_ms);
        const style = index === activeShotIndex
          ? currentState().project.overlay.current_shot_badge
          : currentState().project.overlay.shot_badge;
        const splitText = splitSeconds(splitMs);
        const intervalLabel = splitRowIntervalLabel(splitRow);
        const badgeContent = currentState().project.overlay.show_shot_scores
          ? scoreBadgeContent(shot, index + 1, splitText, intervalLabel)
          : { text: shotBadgeBaseText(index + 1, splitText, intervalLabel), runs: null };
        const shotBadge = badgeElement(
          badgeContent,
          style,
          size,
          null,
          null,
          null,
          shotTextBias,
          overlayScale,
          autoBubbleSize,
        );
        shotBadge.dataset.overlayDrag = "shots";
        appendOverlayBadge(shotBadge, "shots");
      }
    }

    const summary = currentState().scoring_summary || {};
    const imported = summary.imported_stage || {};
    const officialScoreValue = imported.match_type === "idpa" && imported.final_time != null
      ? Number(imported.final_time).toFixed(2)
      : imported.hit_factor != null
        ? Number(imported.hit_factor).toFixed(2)
        : String(summary.display_value || "");
    const officialScoreLabel = imported.match_type === "idpa" ? "Final" : summary.display_label;
    let finalScoreBadge = null;
    if (finalShotReached && currentState().project.scoring.enabled && currentState().project.overlay.show_score && officialScoreValue && officialScoreValue !== "--") {
      const scoreBadge = badgeElement(`${officialScoreLabel} ${officialScoreValue}`, currentState().project.overlay.hit_factor_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);
      scoreBadge.dataset.overlayDrag = "score";
      appendOverlayBadge(scoreBadge, "score", currentState().project.overlay.score_x, currentState().project.overlay.score_y);
      finalScoreBadge = scoreBadge;
    }

    if (usesCustomQuadrant(currentState().project.overlay.shot_quadrant) && overlay.childElementCount > 0) {
      pinCustomOverlayAnchor(overlay, frameRect, {
        x: currentState().project.overlay.custom_x,
        y: currentState().project.overlay.custom_y,
      });
    }

    const textBoxEntries = visibleOverlayTextBoxEntries(finalShotReached);
    const stackAnchorRect = overlayStackAnchorRect(overlay);
    const stackTerminalRect = overlayStackTerminalRect(overlay);

    const nextCustomOverlayKey = textBoxEntries.length === 0
      ? ""
      : customOverlayKey(textBoxEntries, frameClientRect, overlayScale, finalScoreBadge, stackAnchorRect);
    if (!nextCustomOverlayKey) {
      if (customOverlay.childElementCount > 0 || getCustomOverlayRenderKey()) {
        customOverlay.innerHTML = "";
        customOverlay.classList.remove("has-badge");
        setCustomOverlayRenderKey("");
      }
      setTextBoxRenderedPositionById(new Map());
      syncOverlayBadgeCoordinateControlValues();
      return;
    }
    const renderedTextBoxCount = customOverlay.querySelectorAll("[data-text-box-drag='true']").length;
    if (nextCustomOverlayKey !== getCustomOverlayRenderKey() || renderedTextBoxCount !== textBoxEntries.length) {
      renderCustomOverlayBoxes(customOverlay, textBoxEntries, frameClientRect, overlayScale, size, finalScoreBadge, stackAnchorRect, stackTerminalRect);
      setCustomOverlayRenderKey(nextCustomOverlayKey);
    }
    customOverlay.classList.toggle("has-badge", customOverlay.childElementCount > 0);
    syncOverlayBadgeCoordinateControlValues();
    syncLockedTextBoxEditorCoordinates();
  }

  return Object.freeze({
    readOverlayPayload,
    syncOverlayPreviewStateFromControls,
    previewOverlayControlChanges,
    commitOverlayControlChanges,
    clearOverlayColorCommitTimer,
    scheduleOverlayColorCommit,
    flushOverlayColorCommit,
    bindOverlayColorInput,
    syncOverlayCoordinateControlState,
    previewFrameRectForOverlayPlacement,
    overlayBadgeElement,
    overlayBadgeCoordinateFallback,
    resolveRenderedOverlayBadgeCoordinates,
    resetOverlayPlacementBaseline,
    syncOverlayBadgeCoordinateControlValues,
    overlayBadgeLockedToStack,
    previewFrameRectForTextBoxes,
    overlayTextBoxBadge,
    resolveRenderedTextBoxCoordinates,
    unlockedOverlayTextBox,
    syncOverlayBubbleLockControlState,
    syncLockedTextBoxEditorCoordinates,
    visibleOverlayTextBoxEntries,
    overlayTextBoxStyle,
    customOverlayKey,
    overlayStackBadges,
    overlayStackAnchorRect,
    overlayStackTerminalRect,
    firstStackLockedTextBoxRect,
    nextStackLockedTextBoxRect,
    positionStackLockedTextBoxBadge,
    positionTextBoxBadge,
    configureTextBoxGroup,
    renderCustomOverlayBoxes,
    overlayDragConfiguration,
    overlayDragAnchor,
    beginTextBoxDrag,
    moveTextBoxDrag,
    endTextBoxDrag,
    beginOverlayBadgeDrag,
    moveOverlayBadgeDrag,
    endOverlayBadgeDrag,
    renderLiveOverlay,
  });
}
