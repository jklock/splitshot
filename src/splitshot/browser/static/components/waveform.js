export function createWaveformComponent({
  $ = (id) => document.getElementById(id),
  windowObject = window,
  getState = () => null,
  getSelectedShotId = () => null,
  setSelectedShotIdValue = () => {},
  getWaveformMode = () => "select",
  getWaveformZoomX = () => 1,
  getWaveformOffsetMs = () => 0,
  getDraggingShotId = () => null,
  setDraggingShotId = () => {},
  getDraggingShotPointerId = () => null,
  setDraggingShotPointerId = () => {},
  getPendingDragTimeMs = () => null,
  setPendingDragTimeMs = () => {},
  getWaveformPanDrag = () => null,
  setWaveformPanDrag = () => {},
  getWaveformNavigatorDrag = () => null,
  setWaveformNavigatorDrag = () => {},
  getWaveformShotAmplitudeById = () => ({}),
  waveformState = {},
  currentPrimaryVideoPositionMs = () => 0,
  selectShot = () => {},
  capturePointer = () => {},
  releasePointer = () => {},
  withPreservedScrollState = (_targets, render) => render(),
  seconds = (value) => String(value),
  formatConfidenceValue = (value) => String(value),
  isLowConfidence = () => false,
  activity = () => {},
  callApi = () => {},
  deleteShotById = () => {},
  scheduleInteractionPreviewRender = () => {},
  flushInteractionPreviewRender = () => {},
  flushQueuedProjectUiStateApply = () => {},
  flushDeferredRender = () => {},
  panDragThresholdPx = 4,
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function durationMs() {
    return waveformState?.durationMs?.() || 1;
  }

  function selectedShot() {
    return (currentState()?.project?.analysis?.shots || []).find((shot) => shot.id === getSelectedShotId()) || null;
  }

  function selectedShotRange() {
    const shots = currentState()?.project?.analysis?.shots || [];
    const selectedIndex = shots.findIndex((shot) => shot.id === getSelectedShotId());
    if (selectedIndex < 0) return null;

    const shot = shots[selectedIndex];
    const previousTime = selectedIndex > 0 ? shots[selectedIndex - 1].time_ms : 0;
    const nextTime = selectedIndex < shots.length - 1 ? shots[selectedIndex + 1].time_ms : durationMs();

    return {
      shotId: shot.id,
      start: selectedIndex === 0 ? 0 : Math.max(0, Math.round((previousTime + shot.time_ms) / 2)),
      end: selectedIndex === shots.length - 1
        ? durationMs()
        : Math.min(durationMs(), Math.round((shot.time_ms + nextTime) / 2)),
    };
  }

  function waveformAmplitudeForTime(timeMs) {
    const range = selectedShotRange();
    if (!range || timeMs < range.start || timeMs > range.end) return 1;
    return getWaveformShotAmplitudeById()?.[range.shotId] ?? 1;
  }

  function waveformShotSubtitle(segment) {
    const sourceLabel = segment.card_subtitle === "Manual" || segment.card_subtitle === "ShotML"
      ? segment.card_subtitle
      : segment.card_subtitle
        ? `Conf ${segment.card_subtitle}`
        : "";
    return [segment.interval_label || "Split", sourceLabel].filter(Boolean).join(" • ");
  }

  function waveformCanvasDisplayHeight(canvas) {
    const panel = canvas.closest(".waveform-panel");
    if (!panel) return 0;
    const panelHeight = panel.clientHeight || panel.getBoundingClientRect().height || 0;
    if (!panelHeight) return 0;
    const headerHeight = panel.querySelector(".waveform-header")?.getBoundingClientRect().height || 0;
    const windowHeight = panel.querySelector(".waveform-window")?.getBoundingClientRect().height || 0;
    const footerHeight = panel.querySelector(".waveform-footer")?.getBoundingClientRect().height || 0;
    const shotList = panel.querySelector(".waveform-shot-list");
    const shotListVisible = shotList && windowObject.getComputedStyle(shotList).display !== "none";
    const shotListHeight = shotListVisible ? shotList.getBoundingClientRect().height : 0;
    return Math.max(1, Math.floor(panelHeight - headerHeight - windowHeight - footerHeight - shotListHeight));
  }

  function resizeCanvasToDisplay(canvas) {
    const rect = canvas.getBoundingClientRect();
    const parentRect = canvas.parentElement?.getBoundingClientRect();
    const width = Math.max(1, Math.floor(parentRect?.width || canvas.parentElement?.clientWidth || rect.width || canvas.clientWidth || 1600));
    const height = Math.max(1, Math.floor(waveformCanvasDisplayHeight(canvas) || rect.height || canvas.clientHeight || 260));
    const scale = Math.max(1, windowObject.devicePixelRatio || 1);
    const targetWidth = Math.max(1, Math.round(width * scale));
    const targetHeight = Math.max(1, Math.round(height * scale));
    if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
      canvas.width = targetWidth;
      canvas.height = targetHeight;
    }
    canvas.style.width = "100%";
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    return { width, height };
  }

  function renderWaveformPlayhead(positionMs = currentPrimaryVideoPositionMs()) {
    const canvas = $("waveform");
    const playhead = $("waveform-playhead");
    const panel = canvas?.closest(".waveform-panel");
    if (!(canvas instanceof HTMLCanvasElement) || !(playhead instanceof HTMLElement) || !(panel instanceof HTMLElement)) return;
    const total = durationMs();
    const visible = waveformState?.waveformWindow?.() || { start: 0, end: 0, duration: 0 };
    const currentPositionMs = Math.max(0, Math.min(total, Number(positionMs) || 0));
    const canvasRect = canvas.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();
    const withinWindow = currentPositionMs >= visible.start && currentPositionMs <= visible.end;
    const isVisible = canvasRect.width > 0 && canvasRect.height > 0 && visible.duration > 0 && total > 0 && withinWindow;
    playhead.hidden = !isVisible;
    if (!isVisible) return;
    const left = canvasRect.left - panelRect.left + (((currentPositionMs - visible.start) / visible.duration) * canvasRect.width);
    playhead.style.left = `${left}px`;
    playhead.style.top = `${canvasRect.top - panelRect.top}px`;
    playhead.style.height = `${canvasRect.height}px`;
  }

  function drawOutlinedText(ctx, text, x, y, fillStyle, font, lineWidth = 3) {
    ctx.save();
    ctx.font = font;
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.lineJoin = "round";
    ctx.miterLimit = 2;
    ctx.strokeStyle = "rgba(0, 0, 0, 0.88)";
    ctx.lineWidth = lineWidth;
    ctx.fillStyle = fillStyle;
    ctx.strokeText(text, x, y);
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  function drawMarker(ctx, timeMs, color, label, labelColor = "rgba(248, 250, 252, 0.96)", width = null, height = null) {
    if (!(waveformState?.isWaveformVisible?.(timeMs) ?? false)) return;
    const x = waveformState?.waveformX?.(timeMs, width ?? ctx.canvas.width) ?? 0;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height ?? ctx.canvas.height);
    ctx.stroke();
    if (label) {
      drawOutlinedText(
        ctx,
        label,
        x + 5,
        11,
        labelColor,
        "800 12px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
      );
    }
  }

  function drawWaveformScale(ctx, visible, width, height) {
    const tickCount = Math.max(4, Math.min(12, Math.floor(width / 140)));
    ctx.strokeStyle = "rgba(255,255,255,0.14)";
    ctx.fillStyle = "rgba(244,245,246,0.82)";
    ctx.lineWidth = 1;
    ctx.font = "800 11px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif";
    for (let index = 0; index <= tickCount; index += 1) {
      const x = (index / tickCount) * width;
      const timeMs = visible.start + ((index / tickCount) * visible.duration);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
      drawOutlinedText(
        ctx,
        `${(timeMs / 1000).toFixed(3)}s`,
        x + 4,
        height - 17,
        "rgba(226, 232, 240, 0.88)",
        "800 11px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
        3,
      );
    }
  }

  function drawSelectedRegion(ctx, width, height) {
    const shot = selectedShot();
    if (!shot) return;
    if (!(waveformState?.isWaveformVisible?.(shot.time_ms) ?? false)) return;
    const x = waveformState?.waveformX?.(shot.time_ms, width) ?? 0;
    ctx.fillStyle = "rgba(255, 123, 34, 0.18)";
    ctx.fillRect(Math.max(0, x - 44), 0, 88, height);
  }

  function drawWaveformLane(ctx, waveform, {
    width,
    visible,
    totalDuration,
    laneTop,
    laneHeight,
    color,
    baselineColor = color,
    timeOffsetMs = 0,
    amplitudeForTime = () => 1,
  }) {
    if (!Array.isArray(waveform) || waveform.length === 0 || laneHeight <= 0) return;

    const laneCenter = laneTop + (laneHeight / 2);
    const laneAmplitude = laneHeight * 0.38;
    const lastIndex = Math.max(1, waveform.length - 1);

    ctx.strokeStyle = baselineColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, laneCenter);
    ctx.lineTo(width, laneCenter);
    ctx.stroke();

    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();

    for (let index = 0; index < waveform.length; index += 1) {
      const value = Number(waveform[index] || 0);
      const sampleTime = (index / lastIndex) * totalDuration;
      const alignedTime = sampleTime - timeOffsetMs;
      if (alignedTime < visible.start || alignedTime > visible.end) continue;
      const x = waveformState?.waveformX?.(alignedTime, width) ?? 0;
      const amp = value * amplitudeForTime(alignedTime);
      const yTop = laneCenter - (amp * laneAmplitude);
      const yBottom = laneCenter + (amp * laneAmplitude);
      ctx.moveTo(x, yTop);
      ctx.lineTo(x, yBottom);
    }

    ctx.stroke();
  }

  function renderWaveformShotList() {
    const list = $("waveform-shot-list");
    if (!list) return;
    withPreservedScrollState([list], () => {
      list.innerHTML = "";
      (currentState().timing_segments || []).forEach((segment) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "waveform-shot-card";
        if (segment.shot_id === getSelectedShotId()) item.classList.add("selected");
        if (isLowConfidence(segment.confidence, segment.source)) {
          item.classList.add("low-confidence");
          item.title = `Review this split manually: model confidence ${formatConfidenceValue(segment.confidence)}.`;
        }

        const summary = document.createElement("span");
        summary.className = "waveform-shot-card-header";

        const title = document.createElement("strong");
        title.textContent = segment.card_title;

        const value = document.createElement("span");
        value.className = "waveform-shot-card-value";
        value.textContent = `${segment.card_value}s`;

        summary.append(title, value);

        const subtitle = document.createElement("span");
        subtitle.className = "waveform-shot-card-subtitle";
        subtitle.textContent = waveformShotSubtitle(segment);

        const meta = document.createElement("small");
        meta.className = "waveform-shot-card-meta";
        meta.textContent = segment.card_meta;

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "danger-button waveform-shot-delete";
        deleteBtn.textContent = "×";
        deleteBtn.title = "Delete this shot";
        deleteBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          deleteShotById(segment.shot_id, "waveform");
        });

        item.append(summary, subtitle, meta, deleteBtn);
        item.addEventListener("click", () => selectShot(segment.shot_id, { revealInWaveform: true, centerWaveform: true }));
        list.appendChild(item);
      });
    });
  }

  function renderWaveformNavigator() {
    const nav = $("waveform-window");
    const track = $("waveform-window-track");
    const handle = $("waveform-window-handle");
    const expanded = $("cockpit-root")?.classList.contains("waveform-expanded") ?? false;
    if (!nav || !track || !handle) return;
    nav.hidden = !expanded || !currentState()?.project;
    if (nav.hidden) return;
    const metrics = waveformState?.waveformNavigatorMetrics?.(track);
    if (!metrics) return;
    const canPan = metrics.maxOffset > 0;
    nav.classList.toggle("interactive", canPan);
    track.classList.toggle("interactive", canPan);
    handle.classList.toggle("interactive", canPan);
    handle.style.width = `${metrics.handleWidth}px`;
    handle.style.transform = `translateX(${metrics.left}px)`;
    const startLabel = `${(metrics.visible.start / 1000).toFixed(2)}s`;
    const endLabel = `${(metrics.visible.end / 1000).toFixed(2)}s`;
    track.title = canPan
      ? `Drag to pan the zoomed waveform window (${startLabel} to ${endLabel}).`
      : `Zoom in to pan the waveform window (${startLabel} to ${endLabel}).`;
  }

  function renderWaveform() {
    const canvas = $("waveform");
    const { width, height } = resizeCanvasToDisplay(canvas);
    const ctx = canvas.getContext("2d");
    const waveform = currentState()?.project?.analysis?.waveform_primary || [];
    const secondaryWaveform = currentState()?.project?.analysis?.waveform_secondary || [];
    const secondarySourceId = String(currentState()?.project?.analysis?.analyzed_secondary_source_id || "");
    const hasSecondaryWaveform = secondaryWaveform.length > 0
      && (Boolean(secondarySourceId) || (currentState()?.project?.merge_sources || []).length > 0);
    const expanded = $("cockpit-root")?.classList.contains("waveform-expanded") ?? false;
    canvas.classList.toggle("waveform-pannable", expanded && getWaveformZoomX() > 1);
    canvas.classList.toggle("waveform-panning", Boolean(getWaveformPanDrag()));
    canvas.dataset.secondaryWaveform = hasSecondaryWaveform ? "true" : "false";
    canvas.dataset.waveformLaneLayout = hasSecondaryWaveform ? "stacked" : "single";
    canvas.dataset.secondarySourceId = hasSecondaryWaveform ? secondarySourceId : "";
    canvas.dataset.secondaryWaveformSamples = hasSecondaryWaveform ? String(secondaryWaveform.length) : "0";
    const visible = waveformState?.waveformWindow?.() || { start: 0, end: durationMs(), duration: durationMs() };
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#102033";
    ctx.fillRect(0, 0, width, height);
    drawWaveformScale(ctx, visible, width, height);
    drawSelectedRegion(ctx, width, height);
    const totalDuration = Math.max(1, durationMs());
    const laneGap = hasSecondaryWaveform ? Math.max(12, Math.round(height * 0.06)) : 0;
    const primaryLaneHeight = hasSecondaryWaveform ? Math.max(72, Math.round(height * 0.54)) : height;
    const secondaryLaneTop = primaryLaneHeight + laneGap;
    const secondaryLaneHeight = hasSecondaryWaveform ? Math.max(44, height - secondaryLaneTop - 20) : 0;

    if (hasSecondaryWaveform) {
      const separatorY = Math.max(0, secondaryLaneTop - Math.max(4, Math.round(laneGap / 2)));
      ctx.strokeStyle = "rgba(226, 232, 240, 0.16)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, separatorY);
      ctx.lineTo(width, separatorY);
      ctx.stroke();
      drawOutlinedText(
        ctx,
        "Primary",
        12,
        10,
        "rgba(58, 160, 255, 0.94)",
        "800 11px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
        3,
      );
      const syncOffsetMs = Math.round(Number(currentState()?.project?.analysis?.sync_offset_ms) || 0);
      drawOutlinedText(
        ctx,
        `Secondary \u2022 ${syncOffsetMs > 0 ? "+" : ""}${syncOffsetMs} ms`,
        12,
        secondaryLaneTop + 6,
        "rgba(57, 208, 111, 0.96)",
        "800 11px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
        3,
      );
    }

    drawWaveformLane(ctx, waveform, {
      width,
      visible,
      totalDuration,
      laneTop: 0,
      laneHeight: primaryLaneHeight,
      color: "#3aa0ff",
      baselineColor: "rgba(58, 160, 255, 0.18)",
      amplitudeForTime: waveformAmplitudeForTime,
    });

    if (hasSecondaryWaveform) {
      drawWaveformLane(ctx, secondaryWaveform, {
        width,
        visible,
        totalDuration,
        laneTop: secondaryLaneTop,
        laneHeight: secondaryLaneHeight,
        color: "#39d06f",
        baselineColor: "rgba(57, 208, 111, 0.24)",
        timeOffsetMs: Math.round(Number(currentState()?.project?.analysis?.sync_offset_ms) || 0),
      });
    }

    const beep = waveformBeepDragging
      ? (getPendingDragTimeMs() ?? currentState()?.project?.analysis?.beep_time_ms_primary)
      : (currentState()?.project?.analysis?.beep_time_ms_primary);
    if (beep !== null && beep !== undefined) {
      const beepColor = waveformBeepDragging ? "#ff9f4a" : "#ff7b22";
      const beepLabel = waveformBeepDragging ? `BEEP ${seconds(beep)}` : "BEEP";
      drawMarker(ctx, beep, beepColor, beepLabel, "rgba(226, 232, 240, 0.88)", width, height);
    }
    const shots = currentState()?.project?.analysis?.shots || [];
    const draggedShotId = getDraggingShotId();
    const pendingDragTimeMs = getPendingDragTimeMs();
    const draggedShotIndex = draggedShotId
      ? shots.findIndex((shot) => shot.id === draggedShotId)
      : -1;
    shots.forEach((shot, index) => {
      const selected = shot.id === getSelectedShotId();
      const timeMs = draggedShotIndex >= 0 && index === draggedShotIndex && pendingDragTimeMs !== null
        ? pendingDragTimeMs
        : shot.time_ms;
      const label = expanded ? `${index + 1} ${seconds(timeMs)}` : "";
      drawMarker(
        ctx,
        timeMs,
        selected ? "#ffffff" : "#39d06f",
        label,
        selected ? "rgba(248, 250, 252, 0.98)" : "rgba(226, 232, 240, 0.88)",
        width,
        height,
      );
    });
    renderWaveformShotList();
    renderWaveformNavigator();
    renderWaveformPlayhead();
  }

  function startWaveformPanDrag(event) {
    const canvas = $("waveform");
    setWaveformPanDrag({
      target: canvas,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startOffsetMs: getWaveformOffsetMs(),
      moved: false,
    });
    capturePointer(canvas, event.pointerId);
    canvas.classList.add("waveform-panning");
    activity("waveform.pan_drag.start", { offset_ms: getWaveformOffsetMs() });
    event.preventDefault();
  }

  function updateWaveformPanDrag(event) {
    const drag = getWaveformPanDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    const canvas = $("waveform");
    const rect = canvas.getBoundingClientRect();
    const visible = waveformState?.waveformWindow?.() || { duration: durationMs() };
    const deltaPx = event.clientX - drag.startClientX;
    if (Math.abs(deltaPx) >= panDragThresholdPx) drag.moved = true;
    if (!drag.moved) return;
    const nextOffset = drag.startOffsetMs - ((deltaPx / Math.max(1, rect.width)) * visible.duration);
    waveformState?.setWaveformOffset?.(nextOffset);
    scheduleInteractionPreviewRender({ waveform: true });
  }

  function finishWaveformPanDrag(event) {
    const drag = getWaveformPanDrag();
    if (!drag) return false;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return true;
    releasePointer(drag.target, drag.pointerId);
    drag.target?.classList.remove("waveform-panning");
    const moved = drag.moved;
    setWaveformPanDrag(null);
    if (moved) {
      activity("waveform.pan_drag.commit", { offset_ms: getWaveformOffsetMs() });
      flushInteractionPreviewRender();
    }
    flushQueuedProjectUiStateApply();
    flushDeferredRender();
    return moved;
  }

  function handleWaveformNavigatorPointerDown(event) {
    if (event.button !== 0) return;
    const track = $("waveform-window-track");
    const metrics = waveformState?.waveformNavigatorMetrics?.(track);
    if (!metrics || metrics.maxOffset <= 0) return;
    setWaveformNavigatorDrag({
      target: track,
      pointerId: event.pointerId,
    });
    capturePointer(track, event.pointerId);
    waveformState?.updateWaveformNavigator?.(event.clientX);
    scheduleInteractionPreviewRender({ waveform: true });
    event.preventDefault();
  }

  function moveWaveformNavigatorDrag(event) {
    const drag = getWaveformNavigatorDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    waveformState?.updateWaveformNavigator?.(event.clientX);
    scheduleInteractionPreviewRender({ waveform: true });
  }

  function endWaveformNavigatorDrag(event) {
    const drag = getWaveformNavigatorDrag();
    if (!drag) return;
    if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    releasePointer(drag.target, drag.pointerId);
    setWaveformNavigatorDrag(null);
    flushInteractionPreviewRender();
    flushQueuedProjectUiStateApply();
    flushDeferredRender();
  }

  let waveformBeepDragging = false;

  function handleWaveformPointerDown(event) {
    if (event.button !== 0) return;
    $("waveform").focus();
    const time_ms = waveformState?.waveformTime?.(event) ?? 0;
    if (getWaveformMode() === "add") {
      activity("waveform.add_shot", { time_ms });
      callApi("/api/shots/add", { time_ms });
      return;
    }
    const beep = waveformState?.nearestBeep?.(event) || null;
    if (beep) {
      setSelectedShotIdValue(null);
      waveformBeepDragging = true;
      setPendingDragTimeMs(beep.time_ms);
      capturePointer($("waveform"), event.pointerId);
      activity("waveform.beep_drag_start", { time_ms: beep.time_ms });
      renderWaveform();
      return;
    }
    const shot = waveformState?.nearestShot?.(event) || null;
    if (shot) {
      setSelectedShotIdValue(shot.id);
      setDraggingShotId(shot.id);
      setDraggingShotPointerId(event.pointerId);
      setPendingDragTimeMs(shot.time_ms);
      capturePointer($("waveform"), event.pointerId);
      activity("waveform.drag_start", { shot_id: shot.id, time_ms: shot.time_ms });
      callApi("/api/shots/select", { shot_id: shot.id });
      renderWaveform();
      return;
    }
    if (($("cockpit-root")?.classList.contains("waveform-expanded") ?? false) && getWaveformZoomX() > 1) {
      startWaveformPanDrag(event);
      return;
    }
    const video = $("primary-video");
    if (currentState()?.media?.primary_available) {
      video.currentTime = time_ms / 1000;
      activity("waveform.seek", { time_ms });
    }
  }

  function handleWaveformPointerMove(event) {
    if (getWaveformNavigatorDrag()) {
      moveWaveformNavigatorDrag(event);
      return;
    }
    if (getWaveformPanDrag()) {
      updateWaveformPanDrag(event);
      return;
    }
    if (waveformBeepDragging) {
      setPendingDragTimeMs(waveformState?.waveformTime?.(event) ?? 0);
      scheduleInteractionPreviewRender({ waveform: true });
      return;
    }
    if (!getDraggingShotId()) return;
    if (event.pointerId !== undefined && getDraggingShotPointerId() !== undefined && event.pointerId !== getDraggingShotPointerId()) return;
    setPendingDragTimeMs(waveformState?.waveformTime?.(event) ?? 0);
    scheduleInteractionPreviewRender({ waveform: true });
  }

  function handleWaveformPointerUp(event) {
    if (getWaveformNavigatorDrag()) {
      endWaveformNavigatorDrag(event);
      return;
    }
    if (getWaveformPanDrag()) {
      const moved = finishWaveformPanDrag(event);
      if (!moved) {
        const time_ms = waveformState?.waveformTime?.(event) ?? 0;
        const video = $("primary-video");
        if (currentState()?.media?.primary_available) {
          video.currentTime = time_ms / 1000;
          activity("waveform.seek", { time_ms });
        }
      }
      return;
    }
    if (waveformBeepDragging) {
      waveformBeepDragging = false;
      const timeMs = getPendingDragTimeMs() ?? (waveformState?.waveformTime?.(event) ?? 0);
      flushInteractionPreviewRender();
      setPendingDragTimeMs(null);
      releasePointer($("waveform"), event.pointerId);
      activity("waveform.beep_drag_commit", { time_ms: timeMs });
      callApi("/api/beep", { time_ms: timeMs });
      return;
    }
    if (!getDraggingShotId()) return;
    if (event.pointerId !== undefined && getDraggingShotPointerId() !== undefined && event.pointerId !== getDraggingShotPointerId()) return;
    const shotId = getDraggingShotId();
    const timeMs = getPendingDragTimeMs() ?? (waveformState?.waveformTime?.(event) ?? 0);
    flushInteractionPreviewRender();
    setDraggingShotId(null);
    setDraggingShotPointerId(null);
    setPendingDragTimeMs(null);
    releasePointer($("waveform"), event.pointerId);
    activity("waveform.drag_commit", { shot_id: shotId, time_ms: timeMs });
    callApi("/api/shots/move", { shot_id: shotId, time_ms: timeMs, preserve_following_splits: true });
  }

  return Object.freeze({
    waveformCanvasDisplayHeight,
    resizeCanvasToDisplay,
    renderWaveformPlayhead,
    renderWaveform,
    drawOutlinedText,
    drawMarker,
    drawWaveformScale,
    drawSelectedRegion,
    startWaveformPanDrag,
    updateWaveformPanDrag,
    finishWaveformPanDrag,
    handleWaveformNavigatorPointerDown,
    moveWaveformNavigatorDrag,
    endWaveformNavigatorDrag,
    selectedShotRange,
    waveformAmplitudeForTime,
    waveformShotSubtitle,
    renderWaveformShotList,
    handleWaveformPointerDown,
    handleWaveformPointerMove,
    handleWaveformPointerUp,
  });
}
