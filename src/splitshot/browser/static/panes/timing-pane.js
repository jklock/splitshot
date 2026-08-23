import { createPaneBase } from "./pane-base.js";

export function createTimingPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  getSelectedShotId = () => null,
  setSelectedShotIdValue = () => {},
  getPendingSelectionFallback = () => null,
  setPendingSelectionFallback = () => {},
  getTimingRowEdits = () => new Set(),
  getTimingAdjustmentDrafts = () => new Map(),
  getScoringRowEdits = () => new Set(),
  getTimingColumnWidths = () => ({}),
  setTimingColumnWidths = () => {},
  getTimingColumnResize = () => null,
  setTimingColumnResize = () => {},
  getTimingExpanded = () => false,
  activity = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  scheduleReviewStageRestore = () => {},
  capturePointer = () => {},
  releasePointer = () => {},
  withPreservedScrollState = (_elements, callback) => callback(),
  callApi = () => {},
  selectShot = () => {},
  orderedShotsByTime = () => [],
  seconds = (value) => String(value ?? ""),
  numericMs = (value) => value,
  formatConfidenceValue = (value) => String(value ?? ""),
  isLowConfidence = () => false,
  defaultTimingEventLabel = (kind) => String(kind || "Event"),
  timingEventKindLabel = (kind) => String(kind || "Event"),
  timingEventPlacementText = () => "",
  shotSelectionContext = () => null,
  syncExpandWaveformButton = () => {},
  renderTimingTables = () => {},
  toggleTimingRowEdit = () => {},
  resolvedTimingColumnWidths = (data = {}) => data,
  timingGridTemplate = () => "",
  scoringWorkbenchGridTemplate = () => "",
  timingColumnDefaults = {},
  timingColumnMinWidths = {},
  timingResizableColumns = new Set(),
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function selectedShotId() {
    return getSelectedShotId() || null;
  }

  function timingRowEdits() {
    return getTimingRowEdits() || new Set();
  }

  function timingAdjustmentDrafts() {
    return getTimingAdjustmentDrafts() || new Map();
  }

  function scoringRowEdits() {
    return getScoringRowEdits() || new Set();
  }

  const paneBase = createPaneBase({
    $,
    getRoot: () => $("cockpit-root"),
    getExpandedState: () => Boolean(getTimingExpanded()),
    setExpandedState: () => {},
    expandedClass: "timing-expanded",
    sectionId: "timing-workbench",
    collapseClasses: ["waveform-expanded", "metrics-expanded", "scoring-expanded", "markers-expanded"],
    syncUiState: () => {
      syncExpandWaveformButton();
      syncLocalProjectUiState();
    },
    persistUiState: () => {
      scheduleProjectUiStateApply();
    },
    activity,
    activityName: "timing.expand",
    onExpand: () => {
      syncExpandWaveformButton();
      renderTimingTables();
    },
    onCollapse: () => {
      syncExpandWaveformButton();
      scheduleReviewStageRestore();
    },
  });

  function applyTimingTableColumns(table) {
    if (!table) return;
    if (windowObject.innerWidth <= 680) {
      table.style.removeProperty("grid-template-columns");
      return;
    }
    const template = table.id === "scoring-workbench-table"
      ? scoringWorkbenchGridTemplate(table)
      : timingGridTemplate(table.id);
    if (template) table.style.gridTemplateColumns = template;
  }

  function syncTimingTableColumns() {
    applyTimingTableColumns($("timing-table"));
    applyTimingTableColumns($("timing-workbench-table"));
    applyTimingTableColumns($("scoring-table"));
    applyTimingTableColumns($("scoring-workbench-table"));
  }

  function beginTimingColumnResize(tableId, columnId, event) {
    if (!timingResizableColumns.has(columnId)) return;
    const nextResize = {
      tableId,
      columnId,
      pointerId: event.pointerId,
      startX: event.clientX,
      startWidth: resolvedTimingColumnWidths(getTimingColumnWidths())[columnId] || timingColumnDefaults[columnId] || 96,
      target: event.currentTarget,
    };
    setTimingColumnResize(nextResize);
    capturePointer(nextResize.target, event.pointerId);
    documentObject.body.classList.add("resizing-layout");
    activity("timing.column.resize.start", { table_id: tableId, column_id: columnId });
  }

  function moveTimingColumnResize(event) {
    const resize = getTimingColumnResize();
    if (!resize) return;
    if (event.pointerId !== undefined && resize.pointerId !== undefined && event.pointerId !== resize.pointerId) return;
    const minimumWidth = timingColumnMinWidths[resize.columnId] || 72;
    const nextWidth = Math.max(minimumWidth, Math.round(resize.startWidth + (event.clientX - resize.startX)));
    setTimingColumnWidths({
      ...resolvedTimingColumnWidths(getTimingColumnWidths()),
      [resize.columnId]: nextWidth,
    });
    syncTimingTableColumns();
  }

  function endTimingColumnResize(event) {
    const resize = getTimingColumnResize();
    if (!resize) return;
    if (event.pointerId !== undefined && resize.pointerId !== undefined && event.pointerId !== resize.pointerId) return;
    releasePointer(resize.target, resize.pointerId);
    activity("timing.column.resize.commit", {
      table_id: resize.tableId,
      column_id: resize.columnId,
      width: getTimingColumnWidths()?.[resize.columnId],
    });
    setTimingColumnResize(null);
    documentObject.body.classList.remove("resizing-layout");
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
  }

  function deleteTimingEvent(eventId) {
    activity("timing.event.delete", { event_id: eventId });
    callApi("/api/events/delete", { event_id: eventId });
  }

  function renderTimingEventList() {
    const list = $("timing-event-list");
    if (!list) return;
    withPreservedScrollState([list], () => {
      list.innerHTML = "";
      const events = currentState().project?.analysis?.events || [];
      if (events.length === 0) {
        return;
      }

      events.forEach((event) => {
        const row = documentObject.createElement("div");
        row.className = "timing-event-row";

        const label = documentObject.createElement("strong");
        label.textContent = event.label || defaultTimingEventLabel(event.kind);

        const kind = documentObject.createElement("span");
        kind.textContent = timingEventKindLabel(event.kind);

        const placement = documentObject.createElement("span");
        placement.textContent = timingEventPlacementText(event);

        const remove = documentObject.createElement("button");
        remove.type = "button";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label", `Remove timing event ${event.label || defaultTimingEventLabel(event.kind)}`);
        remove.addEventListener("click", () => deleteTimingEvent(event.id));

        row.append(label, kind, placement, remove);
        list.appendChild(row);
      });
    });
  }

  function renderTimingEventEditor() {
    const shots = orderedShotsByTime();
    const positionSelect = $("timing-event-position");
    const addButton = $("add-timing-event");
    if (!positionSelect || !addButton) return;

    const previousPosition = positionSelect.value;
    const selectedIndex = selectedShotId()
      ? shots.findIndex((shot) => shot.id === selectedShotId())
      : -1;

    positionSelect.innerHTML = "";
    shots.forEach((shot, index) => {
      const beforeOption = documentObject.createElement("option");
      beforeOption.value = `::${shot.id}`;
      beforeOption.textContent = `Before Shot ${index + 1}`;
      positionSelect.appendChild(beforeOption);

      const nextShot = shots[index + 1];
      const afterOption = documentObject.createElement("option");
      afterOption.value = `${shot.id}::${nextShot?.id || ""}`;
      afterOption.textContent = nextShot
        ? `Between Shot ${index + 1} and Shot ${index + 2}`
        : `After Shot ${index + 1}`;
      positionSelect.appendChild(afterOption);
    });

    if (previousPosition && Array.from(positionSelect.options).some((option) => option.value === previousPosition)) {
      positionSelect.value = previousPosition;
    } else if (selectedIndex >= 0) {
      positionSelect.value = `${shots[selectedIndex].id}::${shots[selectedIndex + 1]?.id || ""}`;
    }

    addButton.disabled = shots.length === 0;
    renderTimingEventList();
  }

  function addTimingEvent() {
    const kind = $("timing-event-kind")?.value;
    const labelValue = $("timing-event-label")?.value?.trim?.() || "";
    const [afterShotId = "", beforeShotId = ""] = String($("timing-event-position")?.value || "::").split("::");
    const label = labelValue || defaultTimingEventLabel(kind);
    activity("timing.event.add", { kind, label, after_shot_id: afterShotId, before_shot_id: beforeShotId });
    callApi("/api/events/add", {
      kind,
      label,
      after_shot_id: afterShotId,
      before_shot_id: beforeShotId,
    });
  }

  function restoreOriginalSplit(shotId) {
    setSelectedShotIdValue(shotId);
    timingAdjustmentDrafts().delete(shotId);
    callApi("/api/shots/restore", { shot_id: shotId, preserve_following_splits: false });
  }

  function deleteShotById(shotId, source = "selected") {
    if (!shotId) return;
    if (selectedShotId() === shotId) {
      setPendingSelectionFallback(shotSelectionContext(shotId, currentState(), "index"));
      setSelectedShotIdValue(null);
    }
    timingAdjustmentDrafts().delete(shotId);
    timingRowEdits().delete(shotId);
    scoringRowEdits().delete(shotId);
    if (currentState().project?.ui_state?.selected_shot_id === shotId) currentState().project.ui_state.selected_shot_id = null;
    activity(source === "selected" ? "shot.delete_selected" : "shot.delete_row", { shot_id: shotId, source });
    callApi("/api/shots/delete", { shot_id: shotId });
  }

  function updateTimingRowField(shotId, field, value) {
    if (field === "adjustment_ms") {
      const rows = currentState().split_rows || [];
      const rowIndex = rows.findIndex((row) => row.shot_id === shotId);
      if (rowIndex < 0) return;
      const row = rows[rowIndex];
      const shotmlSplitMs = numericMs(row.shotml_split_ms) ?? numericMs(row.split_ms);
      if (shotmlSplitMs === null || shotmlSplitMs === undefined) return;
      const adjustmentMs = Math.round((Number(value) || 0) * 1000);
      const splitMs = Math.max(0, shotmlSplitMs + adjustmentMs);
      const baseTimeMs = rowIndex === 0
        ? Math.max(0, Number(currentState().project?.analysis?.beep_time_ms_primary ?? 0))
        : Number(rows[rowIndex - 1]?.absolute_time_ms || 0);
      callApi("/api/shots/move", {
        shot_id: shotId,
        time_ms: baseTimeMs + splitMs,
        preserve_following_splits: false,
      });
    }
  }

  function signedSeconds(ms) {
    const value = Number(ms);
    if (!Number.isFinite(value) || value === 0) return "0.00";
    const prefix = value > 0 ? "+" : "-";
    return `${prefix}${(Math.abs(value) / 1000).toFixed(2)}`;
  }

  function splitRowEntryLabel(row) {
    return row.label || (row.shot_number ? `Shot ${row.shot_number}` : row.end_label || "Entry");
  }

  function splitRowRangeLabel(row) {
    return `${row.start_label || "Start"} -> ${row.end_label || (row.shot_number ? `Shot ${row.shot_number}` : "Entry")}`;
  }

  function splitRowIntervalLabel(row) {
    const intervalLabel = String(row?.interval_label || "").trim();
    if (intervalLabel) return intervalLabel;
    if (Number(row?.shot_number || 0) === 1) return "Draw";
    return "Split";
  }

  function splitRowSequenceTotalMs(row) {
    return numericMs(row?.sequence_total_ms);
  }

  function splitRowCumulativeMs(row) {
    const cumulativeMs = numericMs(row?.cumulative_ms);
    if (cumulativeMs !== null && cumulativeMs !== undefined) return cumulativeMs;
    const absoluteMs = numericMs(row?.absolute_time_ms);
    const beepMs = numericMs(currentState().metrics?.beep_ms);
    if (absoluteMs === null || absoluteMs === undefined) return null;
    return beepMs === null || beepMs === undefined ? absoluteMs : Math.max(0, absoluteMs - beepMs);
  }

  function splitRowActions(row) {
    return Array.isArray(row.actions) ? row.actions : [];
  }

  function splitRowActionSummary(row) {
    return splitRowActions(row).map((action) => action.label).filter(Boolean).join(" • ");
  }

  function splitRowPrimaryAction(row) {
    if (row?.event_id) {
      return splitRowActions(row).find((action) => action.event_id === row.event_id) || null;
    }
    return splitRowActions(row).find((action) => action.event_id) || null;
  }

  function splitRowSecondaryActions(row) {
    const primaryAction = splitRowPrimaryAction(row);
    return splitRowActions(row).filter((action) => action !== primaryAction);
  }

  function splitRowPrimaryLabel(row) {
    const primaryAction = splitRowPrimaryAction(row);
    if (primaryAction?.label) return primaryAction.label;
    const intervalLabel = splitRowIntervalLabel(row);
    return intervalLabel && intervalLabel !== "Split" ? intervalLabel : "";
  }

  function splitRowShotMLConfidence(row) {
    if (row?.shotml_confidence === null || row?.shotml_confidence === undefined || row?.shotml_confidence === "") return null;
    const confidence = Number(row?.shotml_confidence);
    return Number.isFinite(confidence) ? confidence : null;
  }

  function splitRowConfidenceLabel(row) {
    const confidence = splitRowShotMLConfidence(row);
    return confidence === null ? "--" : formatConfidenceValue(confidence);
  }

  function splitRowShotMLSplitMs(row) {
    return numericMs(row?.shotml_split_ms) ?? numericMs(row?.split_ms);
  }

  function splitRowShotMLCumulativeMs(row) {
    return numericMs(row?.shotml_cumulative_ms) ?? splitRowCumulativeMs(row);
  }

  function splitRowAdjustmentMs(row) {
    return numericMs(row?.adjustment_ms) ?? 0;
  }

  function splitRowFinalTimeMs(row) {
    return numericMs(row?.final_time_ms) ?? splitRowCumulativeMs(row);
  }

  function maximumSplitRowActionLabelLength() {
    let longest = 8;
    (currentState().split_rows || []).forEach((row) => {
      const labels = [];
      const primaryLabel = splitRowPrimaryLabel(row);
      if (primaryLabel) labels.push(primaryLabel);
      splitRowSecondaryActions(row).forEach((action) => labels.push(action.label || action.kind || "Action"));
      labels.forEach((label) => {
        longest = Math.max(longest, String(label || "").trim().length);
      });
    });
    return longest;
  }

  function buildSplitRowActionCell(row, expandedTable) {
    const cell = documentObject.createElement("div");
    cell.className = "timeline-action-cell";
    const primaryAction = splitRowPrimaryAction(row);
    const primaryLabel = splitRowPrimaryLabel(row);
    const secondaryActions = splitRowSecondaryActions(row);
    if (!expandedTable) {
      cell.textContent = splitRowActionSummary(row) || primaryLabel || "--";
      return cell;
    }

    if (!primaryLabel && secondaryActions.length === 0) {
      cell.textContent = "--";
      return cell;
    }

    const list = documentObject.createElement("div");
    list.className = "timeline-action-list";
    const appendChip = (labelText, { synthetic = false, eventId = null } = {}) => {
      const chip = documentObject.createElement("span");
      chip.className = `timing-action-chip ${synthetic ? "synthetic" : "recorded"}`;
      const chipLabel = documentObject.createElement("span");
      chipLabel.textContent = labelText;
      chip.appendChild(chipLabel);
      if (eventId) {
        const remove = documentObject.createElement("button");
        remove.type = "button";
        remove.className = "timing-action-remove";
        remove.textContent = "×";
        remove.title = `Remove ${labelText || "timing event"}`;
        remove.setAttribute("aria-label", `Remove timing event ${labelText || "action"}`);
        remove.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          deleteTimingEvent(eventId);
        });
        chip.appendChild(remove);
      }
      list.appendChild(chip);
    };

    if (primaryLabel) {
      appendChip(primaryLabel, {
        synthetic: !primaryAction?.event_id,
        eventId: primaryAction?.event_id && !primaryAction.synthetic ? primaryAction.event_id : null,
      });
    }
    secondaryActions.forEach((action) => {
      const labelText = action.label || action.kind || "Action";
      appendChip(labelText, {
        synthetic: action.synthetic,
        eventId: action.event_id && !action.synthetic ? action.event_id : null,
      });
    });
    cell.appendChild(list);
    return cell;
  }

  function buildTimingRowControlCell(row, editing) {
    const cell = documentObject.createElement("div");
    cell.className = "timing-lock-cell";
    if (!row.shot_id) return cell;
    const lockButton = documentObject.createElement("button");
    lockButton.type = "button";
    lockButton.className = `lock-button ${editing ? "unlocked" : "locked"}`;
    lockButton.textContent = editing ? "Lock" : "Unlock";
    lockButton.title = editing ? "Lock row" : "Unlock row";
    lockButton.addEventListener("click", () => toggleTimingRowEdit(row.shot_id));
    cell.appendChild(lockButton);
    return cell;
  }

  function buildTimingDeleteCell(row) {
    const cell = documentObject.createElement("div");
    cell.className = "timing-row-button-cell";
    if (!row.shot_id) return cell;
    const deleteShot = documentObject.createElement("button");
    deleteShot.type = "button";
    deleteShot.className = "danger-button restore-button";
    deleteShot.textContent = "Delete";
    deleteShot.title = "Delete this shot from the run.";
    deleteShot.addEventListener("click", () => deleteShotById(row.shot_id, "timing_row"));
    cell.appendChild(deleteShot);
    return cell;
  }

  function buildTimingRestoreCell(row) {
    const cell = documentObject.createElement("div");
    cell.className = "timing-row-button-cell";
    if (!row.shot_id) return cell;
    const restore = documentObject.createElement("button");
    restore.type = "button";
    restore.className = "restore-button";
    restore.textContent = "Restore";
    restore.title = "Restore this shot to its ShotML timing.";
    restore.addEventListener("click", () => restoreOriginalSplit(row.shot_id));
    cell.appendChild(restore);
    return cell;
  }

  function setTimingExpanded(expanded, { persistUiState = true } = {}) {
    const nextExpanded = paneBase.setExpanded(expanded, { persistUiState });
    syncExpandWaveformButton();
    return nextExpanded;
  }

  return Object.freeze({
    applyTimingTableColumns,
    syncTimingTableColumns,
    beginTimingColumnResize,
    moveTimingColumnResize,
    endTimingColumnResize,
    deleteTimingEvent,
    renderTimingEventList,
    renderTimingEventEditor,
    addTimingEvent,
    restoreOriginalSplit,
    deleteShotById,
    updateTimingRowField,
    signedSeconds,
    splitRowEntryLabel,
    splitRowRangeLabel,
    splitRowIntervalLabel,
    splitRowSequenceTotalMs,
    splitRowCumulativeMs,
    splitRowActions,
    splitRowActionSummary,
    splitRowPrimaryAction,
    splitRowSecondaryActions,
    splitRowPrimaryLabel,
    splitRowConfidenceLabel,
    splitRowShotMLConfidence,
    splitRowShotMLSplitMs,
    splitRowShotMLCumulativeMs,
    splitRowAdjustmentMs,
    splitRowFinalTimeMs,
    maximumSplitRowActionLabelLength,
    buildSplitRowActionCell,
    buildTimingRowControlCell,
    buildTimingDeleteCell,
    buildTimingRestoreCell,
    setTimingExpanded,
  });
}
