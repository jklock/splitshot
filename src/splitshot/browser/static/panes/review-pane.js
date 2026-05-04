export function createReviewPane({
  $ = (id) => document.getElementById(id),
  windowObject = window,
  documentObject = document,
  getState = () => null,
  getReviewTextBoxExpansion = () => new Map(),
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  normalizedCoordinateValue = (value) => value,
  normalizeHexColor = (value) => value,
  clamp = (value, min, max) => Math.min(max, Math.max(min, value)),
  clampNumber = (value, min, max) => Math.min(max, Math.max(min, value)),
  opacityValueFromPercent = (value) => value,
  measureOverlayBadgeContent = () => ({ width: 0, height: 0 }),
  overlayBadgePaddingXPx = 0,
  overlayBadgePaddingYPx = 0,
  aboveFinalTextBoxValue = "above_final",
  customQuadrantValue = "custom",
  usesCustomQuadrant = (value) => value === customQuadrantValue,
  resolveRenderedTextBoxCoordinates = () => null,
  unlockedOverlayTextBox = (box) => box,
  previewOverlayControlChanges = () => {},
  scheduleOverlayApply = () => {},
  applyOverlayTextBoxesDraft = () => {},
  syncControlValue = () => {},
  syncControlChecked = () => {},
  syncOpacityPercentControl = () => {},
  controlIsActive = () => false,
  isColorInput = () => false,
  bindOverlayColorInput = () => {},
  preserveElementViewportAnchor = (_elementOrResolver, callback) => callback(),
  withPreservedScrollState = (_elements, callback) => callback(),
  getReviewStageRestoreFrame = () => null,
  setReviewStageRestoreFrame = () => {},
  getReviewStageRestoreSecondFrame = () => null,
  setReviewStageRestoreSecondFrame = () => {},
  applyLayoutState = () => {},
  renderVideo = () => {},
  renderWaveform = () => {},
  renderTimingTables = () => {},
  renderLiveOverlay = () => {},
  scheduleSecondaryPreviewSync = () => {},
  restoreVideoElementFrame = () => {},
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function currentReviewTextBoxExpansion() {
    return getReviewTextBoxExpansion() || new Map();
  }

  function createOverlayTextBoxId() {
    const generated = windowObject.crypto?.randomUUID?.();
    if (generated) return generated.replace(/-/g, "");
    return `textbox-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 10)}`;
  }

  function overlayTextBoxDisplayText(box) {
    if (box.source === "imported_summary") {
      return box.text || currentState()?.scoring_summary?.imported_overlay_text || "";
    }
    return box.text || "";
  }

  function overlayTextBoxAutoSize(box) {
    const text = overlayTextBoxDisplayText(box).trim();
    if (!text) return { width: 0, height: 0 };
    const measurement = measureOverlayBadgeContent(text);
    return {
      width: Math.ceil(measurement.width + (overlayBadgePaddingXPx * 2)),
      height: Math.ceil(measurement.height + (overlayBadgePaddingYPx * 2)),
    };
  }

  function resolvedOverlayTextBoxSize(box) {
    const explicitWidth = Math.max(0, Number(box?.width || 0));
    const explicitHeight = Math.max(0, Number(box?.height || 0));
    if (explicitWidth > 0 && explicitHeight > 0) {
      return { width: explicitWidth, height: explicitHeight };
    }
    const autoSize = overlayTextBoxAutoSize(box);
    return {
      width: explicitWidth > 0 ? explicitWidth : autoSize.width,
      height: explicitHeight > 0 ? explicitHeight : autoSize.height,
    };
  }

  function syncOverlayTextBoxSizeControls(boxId) {
    const box = overlayTextBoxes().find((item) => item.id === boxId);
    if (!box) return;
    const card = [...documentObject.querySelectorAll(".text-box-card[data-box-id]")].find(
      (element) => element instanceof HTMLElement && element.dataset.boxId === boxId,
    );
    if (!(card instanceof HTMLElement)) return;
    const displayedSize = resolvedOverlayTextBoxSize(box);
    const widthInput = card.querySelector('[data-text-box-field="width"]');
    const heightInput = card.querySelector('[data-text-box-field="height"]');
    if (widthInput instanceof HTMLInputElement && !controlIsActive(widthInput)) syncControlValue(widthInput, displayedSize.width);
    if (heightInput instanceof HTMLInputElement && !controlIsActive(heightInput)) syncControlValue(heightInput, displayedSize.height);
  }

  function normalizeOverlayTextBox(box = {}, index = 0) {
    const normalizedX = normalizedCoordinateValue(box.x);
    const normalizedY = normalizedCoordinateValue(box.y);
    const source = box.source === "imported_summary" ? "imported_summary" : "manual";
    const validQuadrants = new Set([
      aboveFinalTextBoxValue,
      "top_left",
      "top_middle",
      "top_right",
      "middle_left",
      "middle_middle",
      "middle_right",
      "bottom_left",
      "bottom_middle",
      "bottom_right",
      customQuadrantValue,
    ]);
    const fallbackQuadrant = source === "imported_summary" ? aboveFinalTextBoxValue : "top_left";
    const requestedQuadrant = validQuadrants.has(box.quadrant) ? box.quadrant : fallbackQuadrant;
    const usesExplicitCoordinates = requestedQuadrant === customQuadrantValue || normalizedX !== null || normalizedY !== null;
    const width = Math.max(0, Number(box.width || 0));
    const height = Math.max(0, Number(box.height || 0));
    return {
      id: box.id || createOverlayTextBoxId(),
      enabled: Boolean(box.enabled ?? true),
      lock_to_stack: Boolean(box.lock_to_stack ?? false),
      source,
      text: String(box.text || "").slice(0, 500),
      quadrant: usesExplicitCoordinates ? customQuadrantValue : requestedQuadrant,
      x: usesExplicitCoordinates ? normalizedX ?? 0.5 : null,
      y: usesExplicitCoordinates ? normalizedY ?? 0.5 : null,
      background_color: normalizeHexColor(box.background_color || "#000000") || "#000000",
      text_color: normalizeHexColor(box.text_color || "#ffffff") || "#ffffff",
      opacity: clamp(Number(box.opacity ?? 0.9), 0, 1),
      width,
      height,
      order: Number(box.order ?? index),
    };
  }

  function overlayTextBoxes() {
    if (!currentState()?.project?.overlay) return [];
    const boxes = Array.isArray(currentState().project.overlay.text_boxes) ? currentState().project.overlay.text_boxes : [];
    if (boxes.length > 0) {
      return boxes.map((box, index) => normalizeOverlayTextBox(box, index));
    }
    const overlay = currentState().project.overlay;
    const hasLegacyBox = Boolean(
      overlay.custom_box_enabled
        || (overlay.custom_box_mode || "manual") === "imported_summary"
        || overlay.custom_box_text,
    );
    if (!hasLegacyBox) return [];
    return [normalizeOverlayTextBox({
      id: "legacy-custom-box",
      enabled: overlay.custom_box_enabled,
      lock_to_stack: false,
      source: overlay.custom_box_mode || "manual",
      text: overlay.custom_box_text || "",
      quadrant: overlay.custom_box_quadrant || "top_right",
      x: overlay.custom_box_x,
      y: overlay.custom_box_y,
      background_color: overlay.custom_box_background_color || "#000000",
      text_color: overlay.custom_box_text_color || "#ffffff",
      opacity: overlay.custom_box_opacity ?? 0.9,
      width: overlay.custom_box_width || 0,
      height: overlay.custom_box_height || 0,
    })];
  }

  function preferredLegacyTextBox(boxes) {
    return boxes.find((box) => box.source === "imported_summary") || boxes[0] || null;
  }

  function syncLegacyOverlayBoxState(overlay, boxes = overlayTextBoxes()) {
    const primary = preferredLegacyTextBox(boxes);
    if (!primary) {
      overlay.custom_box_enabled = false;
      overlay.custom_box_mode = "manual";
      overlay.custom_box_text = "";
      return;
    }
    overlay.custom_box_enabled = Boolean(primary.enabled);
    overlay.custom_box_mode = primary.source;
    overlay.custom_box_text = primary.text;
    overlay.custom_box_quadrant = primary.quadrant;
    overlay.custom_box_x = primary.x;
    overlay.custom_box_y = primary.y;
    overlay.custom_box_background_color = primary.background_color;
    overlay.custom_box_text_color = primary.text_color;
    overlay.custom_box_opacity = primary.opacity;
    overlay.custom_box_width = primary.width;
    overlay.custom_box_height = primary.height;
  }

  function setLocalOverlayTextBoxes(boxes) {
    if (!currentState()?.project?.overlay) return;
    const normalized = boxes.map((box, index) => normalizeOverlayTextBox(box, index));
    currentState().project.overlay.text_boxes = normalized;
    applyOverlayTextBoxesDraft(normalized);
    syncLegacyOverlayBoxState(currentState().project.overlay, normalized);
  }

  function buildOverlayTextBox(source = "manual") {
    return normalizeOverlayTextBox({
      id: createOverlayTextBoxId(),
      enabled: true,
      lock_to_stack: false,
      source,
      text: "",
      quadrant: source === "imported_summary" ? aboveFinalTextBoxValue : "top_left",
      x: null,
      y: null,
      background_color: "#000000",
      text_color: "#ffffff",
      opacity: 0.9,
      width: 0,
      height: 0,
    });
  }

  function overlayTextBoxLabel(box, index) {
    if (box.source === "imported_summary") return `Imported Summary ${index + 1}`;
    return `Custom Box ${index + 1}`;
  }

  function applyOverlayTextBoxUpdate(boxes, { commit = false, rerender = false } = {}) {
    setLocalOverlayTextBoxes(boxes);
    applyOverlayTextBoxesDraft(boxes);
    previewOverlayControlChanges();
    if (rerender) renderTextBoxEditors();
    if (commit) scheduleOverlayApply();
  }

  function updateOverlayTextBox(boxId, updater, options = {}) {
    const boxes = overlayTextBoxes();
    const index = boxes.findIndex((box) => box.id === boxId);
    if (index === -1) return;
    const nextBox = updater({ ...boxes[index] }, index, boxes);
    if (!nextBox) return;
    const nextBoxes = boxes.slice();
    nextBoxes[index] = normalizeOverlayTextBox(nextBox, index);
    applyOverlayTextBoxUpdate(nextBoxes, options);
  }

  function setOverlayTextBoxField(boxId, field, rawValue, options = {}) {
    updateOverlayTextBox(boxId, (box) => {
      if (field === "enabled") {
        box.enabled = Boolean(rawValue);
        return box;
      }
      if (field === "lock_to_stack") {
        const locked = Boolean(rawValue);
        if (!locked && box.lock_to_stack && box.quadrant !== aboveFinalTextBoxValue) {
          return unlockedOverlayTextBox(box);
        }
        if (locked && !box.lock_to_stack && box.quadrant !== aboveFinalTextBoxValue) {
          const renderedCoordinates = resolveRenderedTextBoxCoordinates(box.id, box);
          if (renderedCoordinates) {
            box.x = renderedCoordinates.x;
            box.y = renderedCoordinates.y;
          }
        }
        box.lock_to_stack = locked;
        return box;
      }
      if (field === "source") {
        box.source = rawValue === "imported_summary" ? "imported_summary" : "manual";
        if (box.source === "imported_summary") {
          if (!usesCustomQuadrant(box.quadrant)) {
            box.quadrant = aboveFinalTextBoxValue;
            box.x = null;
            box.y = null;
          }
        }
        return box;
      }
      if (field === "text") {
        box.text = String(rawValue || "");
        return box;
      }
      if (field === "quadrant") {
        if (usesCustomQuadrant(rawValue)) {
          const renderedCoordinates = resolveRenderedTextBoxCoordinates(box.id, box) || {
            x: normalizedCoordinateValue(box.x) ?? 0.5,
            y: normalizedCoordinateValue(box.y) ?? 0.5,
          };
          box.quadrant = customQuadrantValue;
          box.x = renderedCoordinates.x;
          box.y = renderedCoordinates.y;
        } else {
          box.quadrant = rawValue;
          box.x = null;
          box.y = null;
        }
        return box;
      }
      if (field === "x") {
        box.quadrant = customQuadrantValue;
        box.x = normalizedCoordinateValue(rawValue);
        box.y = box.y ?? 0.5;
        return box;
      }
      if (field === "y") {
        box.quadrant = customQuadrantValue;
        box.x = box.x ?? 0.5;
        box.y = normalizedCoordinateValue(rawValue);
        return box;
      }
      if (field === "width" || field === "height") {
        box[field] = Math.max(0, Number(rawValue || 0));
        return box;
      }
      if (field === "background_color" || field === "text_color") {
        box[field] = normalizeHexColor(rawValue) || box[field];
        return box;
      }
      if (field === "opacity") {
        const numericOpacity = Number(rawValue);
        box.opacity = numericOpacity > 1
          ? opacityValueFromPercent(numericOpacity)
          : clampNumber(numericOpacity || 0, 0, 1);
        return box;
      }
      return box;
    }, options);
    if (["text", "quadrant", "source", "width", "height", "lock_to_stack"].includes(field)) {
      syncOverlayTextBoxSizeControls(boxId);
    }
  }

  function addOverlayTextBox(source = "manual") {
    const boxes = overlayTextBoxes();
    const nextBox = buildOverlayTextBox(source);
    boxes.push(nextBox);
    applyOverlayTextBoxUpdate(boxes, { commit: true, rerender: true });
  }

  function duplicateOverlayTextBox(boxId) {
    const boxes = overlayTextBoxes();
    const index = boxes.findIndex((box) => box.id === boxId);
    if (index === -1) return;
    const duplicate = normalizeOverlayTextBox({
      ...boxes[index],
      id: createOverlayTextBoxId(),
    }, index + 1);
    const nextBoxes = boxes.slice();
    nextBoxes.splice(index + 1, 0, duplicate);
    applyOverlayTextBoxUpdate(nextBoxes, { commit: true, rerender: true });
  }

  function removeOverlayTextBox(boxId) {
    const nextBoxes = overlayTextBoxes().filter((box) => box.id !== boxId);
    applyOverlayTextBoxUpdate(nextBoxes, { commit: true, rerender: true });
  }

  function overlayTextBoxHint(box) {
    const importedReady = Boolean(currentState()?.scoring_summary?.imported_overlay_text);
    if (box.quadrant === aboveFinalTextBoxValue) {
      return box.source === "imported_summary"
        ? "Keeps the imported summary centered above the final score badge once it appears. Edit the text to override the imported copy."
        : "Keeps this box centered above the final score badge once it appears.";
    }
    if (box.lock_to_stack) {
      return "Locked to the shot stack. Disable this to edit placement directly.";
    }
    if (box.source === "imported_summary") {
      return importedReady
        ? "Uses the imported PractiScore stage summary by default and appears after the final shot. Edit the text here to override it."
        : "Import PractiScore results first. The summary box will populate after the final shot, and you can edit it here.";
    }
    return "Uses custom text and the same box model in Review and Export. Switch to Custom placement to edit X and Y directly.";
  }

  function isReviewTextBoxExpanded(boxId) {
    if (!boxId) return false;
    if (currentReviewTextBoxExpansion().has(boxId)) return Boolean(currentReviewTextBoxExpansion().get(boxId));
    return false;
  }

  function setReviewTextBoxExpanded(boxId, expanded) {
    if (!boxId) return;
    currentReviewTextBoxExpansion().set(boxId, Boolean(expanded));
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
  }

  function buildTextBoxCard(box, index) {
    const card = documentObject.createElement("section");
    card.className = "text-box-card";
    card.dataset.boxId = box.id;
    const expanded = isReviewTextBoxExpanded(box.id);
    card.classList.toggle("collapsed", !expanded);
    const boxLockedToStack = Boolean(box.lock_to_stack);
    const displayedCoordinates = boxLockedToStack && box.quadrant !== aboveFinalTextBoxValue
      ? resolveRenderedTextBoxCoordinates(box.id, box)
      : null;
    const displayedSize = resolvedOverlayTextBoxSize(box);
    const usesCustomPlacement = usesCustomQuadrant(box.quadrant);
    card.innerHTML = `
      <div class="text-box-card-header">
        <label class="check-row"><input type="checkbox" data-text-box-field="enabled" /> <strong>${overlayTextBoxLabel(box, index)}</strong></label>
        <div class="text-box-card-actions">
          <button type="button" class="scoring-shot-toggle" data-text-box-action="toggle" aria-label="${expanded ? "Hide" : "Show"} text box editor">${expanded ? "v" : ">"}</button>
          <button type="button" data-text-box-action="duplicate">Duplicate</button>
          <button type="button" data-text-box-action="remove">Remove</button>
        </div>
      </div>
      <div class="text-box-card-body" ${expanded ? "" : "hidden"}>
        <label class="check-row"><input data-text-box-field="lock_to_stack" type="checkbox" /> Lock to shot stack</label>
        <p class="hint" data-text-box-hint="true"></p>
        <label>Content source
          <select data-text-box-field="source">
            <option value="manual">Custom text</option>
            <option value="imported_summary">Imported summary</option>
          </select>
        </label>
        <label>Box text
          <textarea data-text-box-field="text" rows="3"></textarea>
        </label>
        <div class="control-grid">
          <label>Box placement
            <select data-text-box-field="quadrant">
              <option value="above_final">Above Final Box</option>
              <option value="top_left">Top left</option>
              <option value="top_middle">Top middle</option>
              <option value="top_right">Top right</option>
              <option value="middle_left">Middle left</option>
              <option value="middle_middle">Middle middle</option>
              <option value="middle_right">Middle right</option>
              <option value="bottom_left">Bottom left</option>
              <option value="bottom_middle">Bottom middle</option>
              <option value="bottom_right">Bottom right</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          <label>Box X (0 left, 1 right)
            <input data-text-box-field="x" type="number" min="0" max="1" step="0.01" />
          </label>
          <label>Box Y (0 top, 1 bottom)
            <input data-text-box-field="y" type="number" min="0" max="1" step="0.01" />
          </label>
        </div>
        <div class="control-grid">
          <label>Box width
            <input data-text-box-field="width" type="number" min="0" max="1000" step="1" value="0" />
          </label>
          <label>Box height
            <input data-text-box-field="height" type="number" min="0" max="1000" step="1" value="0" />
          </label>
        </div>
        <div class="style-grid review-style-grid">
          <section class="style-card custom-box-style-card">
            <h4>Box Style</h4>
            <label class="color-field"><span class="style-card-label">Background</span>
              <span class="color-control-pair">
                <button data-text-box-field="background_color" class="color-swatch-button" data-color-label="Text box background" type="button"></button>
                <input class="color-hex-input" type="text" inputmode="text" spellcheck="false" value="#000000" placeholder="#000000" aria-label="Text box background hex value" />
              </span>
            </label>
            <label class="color-field"><span class="style-card-label">Text</span>
              <span class="color-control-pair">
                <button data-text-box-field="text_color" class="color-swatch-button" data-color-label="Text box text" type="button"></button>
                <input class="color-hex-input" type="text" inputmode="text" spellcheck="false" value="#ffffff" placeholder="#FFFFFF" aria-label="Text box text hex value" />
              </span>
            </label>
            <label class="opacity-field"><span class="style-card-label">Opacity</span>
              <span class="opacity-control-pair">
                <span class="opacity-percent-field">
                  <input class="opacity-percent-input" data-text-box-field="opacity" type="number" min="0" max="100" step="1" value="90" aria-label="Opacity percent" />
                  <span class="opacity-percent-suffix">%</span>
                </span>
              </span>
            </label>
          </section>
        </div>
      </div>
    `;
    const body = card.querySelector(".text-box-card-body");
    if (body) body.hidden = !expanded;
    syncControlChecked(card.querySelector('[data-text-box-field="enabled"]'), box.enabled);
    syncControlChecked(card.querySelector('[data-text-box-field="lock_to_stack"]'), box.lock_to_stack);
    syncControlValue(card.querySelector('[data-text-box-field="source"]'), box.source);
    syncControlValue(card.querySelector('[data-text-box-field="quadrant"]'), box.quadrant);
    syncControlValue(card.querySelector('[data-text-box-field="x"]'), displayedCoordinates?.x ?? box.x ?? "");
    syncControlValue(card.querySelector('[data-text-box-field="y"]'), displayedCoordinates?.y ?? box.y ?? "");
    syncControlValue(card.querySelector('[data-text-box-field="width"]'), displayedSize.width);
    syncControlValue(card.querySelector('[data-text-box-field="height"]'), displayedSize.height);
    syncControlValue(card.querySelector('[data-text-box-field="background_color"]'), box.background_color);
    syncControlValue(card.querySelector('[data-text-box-field="text_color"]'), box.text_color);
    syncOpacityPercentControl(card.querySelector('[data-text-box-field="opacity"]'), box.opacity ?? 0.9);
    const textArea = card.querySelector('[data-text-box-field="text"]');
    textArea.dataset.importedSummaryDefault = box.source === "imported_summary"
      ? (currentState()?.scoring_summary?.imported_overlay_text || "")
      : "";
    textArea.value = box.text || overlayTextBoxDisplayText(box);
    textArea.disabled = false;
    textArea.placeholder = box.source === "imported_summary"
      ? "Leave blank to use the imported PractiScore stage summary after the final shot"
      : "Text to show over the video";
    const hint = card.querySelector('[data-text-box-hint="true"]');
    if (hint) hint.textContent = overlayTextBoxHint(box);
    const quadrantInput = card.querySelector('[data-text-box-field="quadrant"]');
    quadrantInput.disabled = boxLockedToStack;
    const xInput = card.querySelector('[data-text-box-field="x"]');
    const yInput = card.querySelector('[data-text-box-field="y"]');
    [xInput, yInput].forEach((input) => {
      input.disabled = boxLockedToStack || !usesCustomPlacement;
      input.placeholder = boxLockedToStack ? "Stack locked" : usesCustomPlacement ? "0.50" : "Custom only";
    });
    card.querySelectorAll("[data-text-box-field]").forEach((control) => {
      const field = control.dataset.textBoxField || "";
      if (!field) return;
      if (isColorInput(control)) return;
      const readValue = () => {
        if (control.type === "checkbox") return control.checked;
        if (field === "text" && box.source === "imported_summary") {
          const rawValue = String(control.value || "");
          const importedSummaryDefault = control.dataset.importedSummaryDefault || "";
          return rawValue === importedSummaryDefault ? "" : rawValue;
        }
        return control.value;
      };
      if (control.tagName === "SELECT") {
        control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), {
          commit: true,
          rerender: field === "source" || field === "quadrant",
        }));
        return;
      }
      if (control.type === "checkbox") {
        control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: field === "lock_to_stack" }));
        return;
      }
      if (control.type === "range") {
        control.addEventListener("input", () => setOverlayTextBoxField(box.id, field, readValue(), { rerender: false }));
        control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: false }));
        return;
      }
      control.addEventListener("input", () => setOverlayTextBoxField(box.id, field, readValue(), { rerender: false }));
      control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: false }));
      control.addEventListener("blur", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: false }));
    });
    card.querySelector('[data-text-box-action="toggle"]')?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      preserveElementViewportAnchor(
        () => documentObject.querySelector(`.text-box-card[data-box-id="${box.id}"]`),
        () => {
          setReviewTextBoxExpanded(box.id, !isReviewTextBoxExpanded(box.id));
          renderTextBoxEditors();
        },
      );
    });
    card.querySelector('[data-text-box-action="duplicate"]')?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      duplicateOverlayTextBox(box.id);
    });
    card.querySelector('[data-text-box-action="remove"]')?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      removeOverlayTextBox(box.id);
    });
    bindOverlayColorInput(card.querySelector('[data-text-box-field="background_color"]'));
    bindOverlayColorInput(card.querySelector('[data-text-box-field="text_color"]'));
    return card;
  }

  function renderTextBoxEditors() {
    const containers = [$("review-text-box-list")].filter(Boolean);
    if (containers.length === 0) return;
    const boxes = overlayTextBoxes();
    const validBoxIds = new Set(boxes.map((box) => box.id));
    [...currentReviewTextBoxExpansion().keys()].forEach((boxId) => {
      if (!validBoxIds.has(boxId)) currentReviewTextBoxExpansion().delete(boxId);
    });
    containers.forEach((container) => {
      withPreservedScrollState([container], () => {
        container.innerHTML = "";
        if (boxes.length === 0) {
          const empty = documentObject.createElement("div");
          empty.className = "hint";
          empty.textContent = "No text boxes yet. Add a custom box or an imported summary box here and it will render in both review and export.";
          container.appendChild(empty);
          return;
        }
        boxes.forEach((box, index) => {
          container.appendChild(buildTextBoxCard(box, index));
        });
      });
    });
  }

  function refreshReviewMediaFrame() {
    renderLiveOverlay();
    scheduleSecondaryPreviewSync();
    restoreVideoElementFrame($("primary-video"));
    restoreVideoElementFrame($("secondary-video"));
  }

  function restoreReviewStage() {
    if (!currentState()?.project) return;
    applyLayoutState();
    renderVideo();
    renderWaveform();
    renderTimingTables();
    renderLiveOverlay();
    scheduleSecondaryPreviewSync();
    restoreVideoElementFrame($("primary-video"));
    restoreVideoElementFrame($("secondary-video"));
    documentObject.querySelectorAll("#merge-preview-layer video").forEach((video) => restoreVideoElementFrame(video));
  }

  function scheduleReviewStageRestore() {
    const reviewStageRestoreFrame = getReviewStageRestoreFrame();
    const reviewStageRestoreSecondFrame = getReviewStageRestoreSecondFrame();
    if (reviewStageRestoreFrame !== null) windowObject.cancelAnimationFrame(reviewStageRestoreFrame);
    if (reviewStageRestoreSecondFrame !== null) windowObject.cancelAnimationFrame(reviewStageRestoreSecondFrame);
    setReviewStageRestoreFrame(windowObject.requestAnimationFrame(() => {
      setReviewStageRestoreFrame(null);
      restoreReviewStage();
      setReviewStageRestoreSecondFrame(windowObject.requestAnimationFrame(() => {
        setReviewStageRestoreSecondFrame(null);
        restoreReviewStage();
      }));
    }));
  }

  return Object.freeze({
    createOverlayTextBoxId,
    overlayTextBoxAutoSize,
    resolvedOverlayTextBoxSize,
    syncOverlayTextBoxSizeControls,
    normalizeOverlayTextBox,
    overlayTextBoxes,
    preferredLegacyTextBox,
    syncLegacyOverlayBoxState,
    setLocalOverlayTextBoxes,
    buildOverlayTextBox,
    overlayTextBoxLabel,
    applyOverlayTextBoxUpdate,
    updateOverlayTextBox,
    setOverlayTextBoxField,
    addOverlayTextBox,
    duplicateOverlayTextBox,
    removeOverlayTextBox,
    overlayTextBoxDisplayText,
    overlayTextBoxHint,
    isReviewTextBoxExpanded,
    setReviewTextBoxExpanded,
    buildTextBoxCard,
    renderTextBoxEditors,
    refreshReviewMediaFrame,
    restoreReviewStage,
    scheduleReviewStageRestore,
  });
}
