import { createPaneBase } from "./pane-base.js";

export function createScoringPane({
  $ = (id) => document.getElementById(id),
  windowObject = window,
  getState = () => null,
  getSelectedShotId = () => null,
  setSelectedShotIdValue = () => {},
  getScoringWorkbenchExpanded = () => false,
  setScoringWorkbenchExpandedValue = () => {},
  getScoringRowEdits = () => new Set(),
  setScoringRowEdits = () => {},
  activity = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  scheduleReviewStageRestore = () => {},
  applyTimingTableColumns = () => {},
  withPreservedScrollState = (_elements, callback) => callback(),
  splitRowForShot = () => null,
  splitSeconds = (value) => String(value ?? ""),
  numericMs = (value) => value,
  formatNumber = (value) => String(value ?? ""),
  formatMatchType = (value) => String(value ?? ""),
  formatPractiScoreTime = (value) => String(value ?? ""),
  penaltyFieldLabel = (fieldId, fallback = "") => fallback || fieldId,
  compactScoreDisplay = (letter) => String(letter ?? ""),
  activeScoringRuleset = () => "",
  isLowConfidence = () => false,
  selectShot = () => {},
  splitRowShotMLSplitMs = () => null,
  splitRowSequenceTotalMs = () => null,
  buildSplitRowActionCell = () => document.createElement("div"),
  deleteShotById = () => {},
  restoreOriginalScore = () => {},
  defaultScoreLetter = () => "A",
  collectPenaltyCounts = () => ({}),
  callApi = async () => null,
  refreshReviewMediaFrame = () => {},
  renderDetailsList = () => {},
  practiScoreCompetitors = () => [],
  autoApplyScoring = () => {},
} = {}) {
  const scoringPaneBase = createPaneBase({
    $,
    getExpandedState: getScoringWorkbenchExpanded,
    setExpandedState: setScoringWorkbenchExpandedValue,
    expandedClass: "scoring-expanded",
    sectionId: "scoring-workbench",
    collapseClasses: ["waveform-expanded", "timing-expanded", "metrics-expanded", "markers-expanded"],
    syncUiState: syncLocalProjectUiState,
    persistUiState: scheduleProjectUiStateApply,
    activity,
    activityName: "scoring.expand",
    onExpand: () => {
      windowObject.requestAnimationFrame(() => {
        applyTimingTableColumns($("scoring-workbench-table"));
        windowObject.requestAnimationFrame(() => applyTimingTableColumns($("scoring-workbench-table")));
      });
    },
    onCollapse: () => {
      scheduleReviewStageRestore();
    },
  });

  function currentState() {
    return getState() || {};
  }

  function currentScoringRowEdits() {
    return getScoringRowEdits() || new Set();
  }

  function persistScoringRowEdits(nextShotIds) {
    setScoringRowEdits(new Set(nextShotIds));
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
  }

  function scoringWorkbenchShown() {
    return scoringPaneBase.isExpanded();
  }

  function setScoringWorkbenchExpanded(expanded, { persistUiState = true } = {}) {
    return scoringPaneBase.setExpanded(expanded, { persistUiState });
  }

  function scoringPenaltySummary(segment, penaltyFields = currentState().scoring_summary?.penalty_fields || []) {
    const counts = segment?.penalty_counts || {};
    const parts = penaltyFields
      .map((field) => {
        const count = Number(counts[field.id] || 0);
        return count > 0 ? `${penaltyFieldLabel(field.id, field.label)} ${count}` : "";
      })
      .filter(Boolean);
    return parts.join(" • ") || "--";
  }

  function toggleScoringRowEdit(shotId) {
    if (!shotId) return;
    const nextScoringRowEdits = new Set(currentScoringRowEdits());
    if (nextScoringRowEdits.has(shotId)) nextScoringRowEdits.delete(shotId);
    else nextScoringRowEdits.add(shotId);
    persistScoringRowEdits(nextScoringRowEdits);
    renderScoringTables();
  }

  function applyShotScoringUpdate(shotId, scope) {
    const shot = (currentState().timing_segments || []).find((segment) => segment.shot_id === shotId);
    if (!shot) return Promise.resolve(null);
    const controlScope = (
      scope?.querySelector?.(`[data-score-field="letter"][data-score-shot-id="${shotId}"]`)
        ? scope
        : ($("scoring-workbench-table") || document)
    );
    setSelectedShotIdValue(shotId);
    return callApi("/api/scoring/score", {
      shot_id: shotId,
      letter: controlScope.querySelector(`[data-score-field="letter"][data-score-shot-id="${shotId}"]`)?.value || defaultScoreLetter(),
      penalty_counts: collectPenaltyCounts(controlScope, `.shot-penalty-entry-control[data-score-shot-id="${shotId}"]`),
    }).then((result) => {
      if (result) refreshReviewMediaFrame();
      return result;
    });
  }

  function buildScoringRowControlCell(segment, editing) {
    const cell = document.createElement("div");
    cell.className = "timing-lock-cell";
    const button = document.createElement("button");
    button.type = "button";
    button.className = `lock-button ${editing ? "unlocked" : "locked"}`;
    button.textContent = editing ? "Lock" : "Unlock";
    button.title = editing ? "Lock row" : "Unlock row";
    button.addEventListener("click", () => toggleScoringRowEdit(segment.shot_id));
    cell.appendChild(button);
    return cell;
  }

  function buildScoringDeleteCell(segment) {
    const cell = document.createElement("div");
    cell.className = "timing-row-button-cell";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "danger-button restore-button";
    button.textContent = "Delete";
    button.title = "Delete this shot from the run.";
    button.addEventListener("click", () => deleteShotById(segment.shot_id, "scoring_row"));
    cell.appendChild(button);
    return cell;
  }

  function buildScoringRestoreCell(segment) {
    const cell = document.createElement("div");
    cell.className = "timing-row-button-cell";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "restore-button";
    button.textContent = "Restore";
    button.title = "Restore this shot score and penalties to their original values.";
    button.addEventListener("click", () => restoreOriginalScore(segment.shot_id));
    cell.appendChild(button);
    return cell;
  }

  function buildScoringPenaltyEditor(segment, rowScope, penaltyFields) {
    const wrapper = document.createElement("div");
    wrapper.className = "scoring-penalty-editor";
    const list = document.createElement("div");
    list.className = "scoring-penalty-list";
    const existingEntries = [];
    penaltyFields.forEach((field) => {
      const count = Number(segment.penalty_counts?.[field.id] || 0);
      for (let index = 0; index < count; index += 1) existingEntries.push(field.id);
    });

    function appendPenaltyRow(selectedPenaltyId = "") {
      const row = document.createElement("div");
      row.className = "scoring-penalty-entry";
      const select = document.createElement("select");
      select.className = "shot-penalty-select shot-penalty-entry-control";
      select.dataset.scoreShotId = segment.shot_id;
      select.addEventListener("change", () => applyShotScoringUpdate(segment.shot_id, rowScope));

      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "Select penalty";
      select.appendChild(blank);
      penaltyFields.forEach((field) => {
        const option = document.createElement("option");
        option.value = field.id;
        option.dataset.penaltyId = field.id;
        option.textContent = penaltyFieldLabel(field.id, field.label);
        select.appendChild(option);
      });
      select.value = selectedPenaltyId;
      select.dataset.penaltyId = selectedPenaltyId;
      select.addEventListener("change", () => {
        select.dataset.penaltyId = select.value;
      });

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-penalty-button";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => {
        row.remove();
        if (list.childElementCount === 0) appendPenaltyRow("");
        applyShotScoringUpdate(segment.shot_id, rowScope);
      });
      row.append(select, remove);
      list.appendChild(row);
    }

    if (existingEntries.length > 0) existingEntries.forEach((penaltyId) => appendPenaltyRow(penaltyId));
    else appendPenaltyRow("");

    const add = document.createElement("button");
    add.type = "button";
    add.className = "add-penalty-button";
    add.textContent = "Add Penalty";
    add.addEventListener("click", () => appendPenaltyRow(""));
    wrapper.append(list, add);
    return wrapper;
  }

  function renderScoringTable(tableId = "scoring-table") {
    const table = $(tableId);
    if (!table) return;
    const expandedTable = tableId === "scoring-workbench-table";
    const state = currentState();
    const scoreOptions = state.scoring_summary?.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
    const penaltyFields = state.scoring_summary?.penalty_fields || [];
    const defaultScore = scoreOptions[0] || "A";
    const scoringRowEdits = currentScoringRowEdits();
    const selectedShotId = getSelectedShotId();
    withPreservedScrollState([table], () => {
      table.innerHTML = "";
      table.classList.toggle("timing-resizable-table", expandedTable && tableId !== "scoring-workbench-table");
      applyTimingTableColumns(table);
      const headers = expandedTable
        ? [
          { label: "Edit", columnId: "lock", resizable: false },
          { label: "Shot", columnId: "shot", resizable: false },
          { label: "Current Score", columnId: "score", resizable: false },
          { label: "Penalties", columnId: "penalties", resizable: false },
          { label: "Split", columnId: "split", resizable: false },
          { label: "Run", columnId: "run", resizable: false },
          { label: "Action", columnId: "action", resizable: false },
          { label: "Delete", columnId: "delete", resizable: false },
          { label: "Restore", columnId: "restore", resizable: false },
        ]
        : [
          { label: "Shot", columnId: "shot", resizable: false },
          { label: "Score", columnId: "score", resizable: false },
          { label: "Penalties", columnId: "penalties", resizable: false },
          { label: "Split", columnId: "split", resizable: false },
          { label: "Run", columnId: "run", resizable: false },
          { label: "Action", columnId: "action", resizable: false },
        ];
      headers.forEach((header) => {
        const cell = document.createElement("div");
        cell.className = "head";
        cell.dataset.timingColumn = header.columnId;
        const label = document.createElement("span");
        label.className = "timing-header-label";
        label.textContent = header.label;
        cell.appendChild(label);
        table.appendChild(cell);
      });

      (state.timing_segments || []).forEach((segment) => {
        const splitRow = splitRowForShot(segment.shot_id);
        const editing = expandedTable && scoringRowEdits.has(segment.shot_id);
        const lowConfidence = isLowConfidence(segment.confidence, segment.source);
        const rowScope = document.createElement("div");
        rowScope.className = "scoring-row-scope";
        rowScope.dataset.shotId = segment.shot_id;

        if (expandedTable) table.appendChild(buildScoringRowControlCell(segment, editing));

        const shotCell = document.createElement("div");
        shotCell.className = "timeline-segment-cell";
        shotCell.textContent = `Shot ${segment.shot_number}`;
        if (segment.shot_id === selectedShotId) shotCell.classList.add("selected");
        if (lowConfidence) shotCell.classList.add("low-confidence");
        shotCell.addEventListener("click", () => selectShot(segment.shot_id));
        table.appendChild(shotCell);

        const scoreCell = document.createElement("div");
        if (editing) {
          const select = document.createElement("select");
          select.dataset.scoreField = "letter";
          select.dataset.scoreShotId = segment.shot_id;
          select.className = "shot-score-select";
          scoreOptions.forEach((letter) => {
            const option = document.createElement("option");
            option.value = letter;
            const value = state.scoring_summary?.score_values?.[letter] ?? 0;
            const penalty = state.scoring_summary?.score_penalties?.[letter] ?? 0;
            option.textContent = penalty ? `${letter} (${value}, -${penalty})` : `${letter} (${value})`;
            select.appendChild(option);
          });
          select.value = segment.score_letter || defaultScore;
          select.addEventListener("change", () => applyShotScoringUpdate(segment.shot_id, rowScope));
          rowScope.appendChild(select);
          scoreCell.appendChild(select);
        } else {
          scoreCell.textContent = compactScoreDisplay(segment.score_letter || defaultScore, activeScoringRuleset()) || defaultScore;
        }
        table.appendChild(scoreCell);

        const penaltiesCell = document.createElement("div");
        if (editing && penaltyFields.length > 0) {
          const editor = buildScoringPenaltyEditor(segment, rowScope, penaltyFields);
          rowScope.appendChild(editor);
          penaltiesCell.appendChild(editor);
        } else {
          penaltiesCell.textContent = scoringPenaltySummary(segment, penaltyFields);
        }
        table.appendChild(penaltiesCell);

        const splitCell = document.createElement("div");
        splitCell.textContent = splitSeconds(splitRowShotMLSplitMs(splitRow));
        table.appendChild(splitCell);

        const runCell = document.createElement("div");
        runCell.textContent = splitSeconds(splitRowSequenceTotalMs(splitRow));
        table.appendChild(runCell);

        const actionCell = buildSplitRowActionCell(splitRow || {}, expandedTable);
        if (segment.shot_id === selectedShotId) actionCell.classList.add("selected");
        actionCell.addEventListener("click", () => selectShot(segment.shot_id));
        table.appendChild(actionCell);

        if (!expandedTable) return;
        table.appendChild(buildScoringDeleteCell(segment));
        table.appendChild(buildScoringRestoreCell(segment));
      });
    });
    applyTimingTableColumns(table);
  }

  function renderScoringTables() {
    setScoringWorkbenchExpanded(getScoringWorkbenchExpanded());
    renderScoringTable("scoring-table");
    renderScoringTable("scoring-workbench-table");
  }

  function renderScoringPresetOptions() {
    const select = $("scoring-preset");
    if (!select) return;
    const state = currentState();
    const selected = state.project?.scoring?.ruleset;
    const presets = state.scoring_presets || [];
    const previousLength = select.options.length;
    select.innerHTML = "";
    presets.forEach((preset) => {
      const option = document.createElement("option");
      option.value = preset.id;
      option.textContent = preset.name;
      select.appendChild(option);
    });
    const hasSelected = presets.some((item) => item.id === selected);
    select.value = hasSelected ? selected : (select.options[0]?.value || "");
    const preset = presets.find((item) => item.id === select.value);
    const summary = state.scoring_summary || {};
    const description = $("scoring-description");
    const result = $("scoring-result");
    if (description) description.textContent = preset ? `${preset.sport}: ${preset.description}` : "Choose a scoring preset.";
    if (result) result.textContent = `${summary.display_label}: ${summary.display_value}`;
    renderScoringTables();
    if (previousLength === 0) select.addEventListener("change", renderScoringPresetDescription);
  }

  function renderScoringPresetDescription() {
    const select = $("scoring-preset");
    const description = $("scoring-description");
    if (!select || !description) return;
    const selected = select.value;
    const preset = (currentState().scoring_presets || []).find((item) => item.id === selected);
    description.textContent = preset ? `${preset.sport}: ${preset.description}` : "";
  }

  function importedStageRecordedScoreLabel(imported) {
    if (!imported) return "";
    if (imported.match_type === "idpa") {
      const pointsDown = Number(imported.aggregate_points ?? imported.score_counts?.["Points Down"] ?? 0);
      return Number.isFinite(pointsDown) ? `PD ${formatNumber(pointsDown, 2)}` : "";
    }
    const parts = [];
    const pointsValue = imported.total_points ?? imported.aggregate_points;
    if (pointsValue !== null && pointsValue !== undefined) {
      parts.push(`Points ${formatNumber(pointsValue, 4)}`);
    }
    if (imported.hit_factor !== null && imported.hit_factor !== undefined) {
      parts.push(`Hit Factor ${formatNumber(imported.hit_factor, 4)}`);
    }
    if (imported.stage_points !== null && imported.stage_points !== undefined) {
      parts.push(`Stage Points ${formatNumber(imported.stage_points, 4)}`);
    }
    return parts.join(" • ");
  }

  function importedStagePenaltyLabel(imported) {
    if (!imported) return "";
    const parts = Object.entries(imported.score_counts || {})
      .filter(([, value]) => Number(value || 0) !== 0)
      .map(([label, value]) => `${label} ${formatNumber(value, 2)}`);
    if (imported.match_type !== "idpa" && Number(imported.shot_penalties || 0) !== 0) {
      parts.unshift(`Penalty ${formatNumber(imported.shot_penalties, 2)}`);
    }
    return parts.join(" • ") || "None";
  }

  function renderOwnedSummaryList(id, rows = [], className = "") {
    const list = $(id);
    if (!(list instanceof HTMLElement)) return;
    list.className = ["details", "pane-summary-list", className].filter(Boolean).join(" ");
    list.replaceChildren();
    rows.forEach(([label, value]) => {
      const term = document.createElement("dt");
      term.textContent = label;
      const description = document.createElement("dd");
      description.textContent = value;
      list.append(term, description);
    });
  }

  function renderPractiScoreSummaries() {
    const state = currentState();
    const imported = state.scoring_summary?.imported_stage;
    if (!imported) {
      renderOwnedSummaryList("scoring-imported-summary", [], "scoring-imported-summary");
      return;
    }
    const stageLabel = imported.stage_name
      ? `Stage ${imported.stage_number}: ${imported.stage_name}`
      : `Stage ${imported.stage_number}`;
    renderOwnedSummaryList("scoring-imported-summary", [
      ["Source", imported.source_name || "Selected file"],
      ["Stage", stageLabel],
      ["Competitor", imported.competitor_name],
      ["PS - Score", importedStageRecordedScoreLabel(imported)],
      ["PS - Penalties", importedStagePenaltyLabel(imported)],
    ], "scoring-imported-summary");
  }

  function readScoringPayload() {
    const state = currentState();
    return {
      enabled: $("scoring-enabled")?.checked ?? Boolean(state.project?.scoring?.enabled),
      penalties: $("penalties") ? Number($("penalties").value || 0) : Number(state.project?.scoring?.penalties || 0),
      penalty_counts: { ...(state.project?.scoring?.penalty_counts || {}) },
    };
  }

  async function applyScoringSettings(scoringPayload = readScoringPayload(), ruleset = $("scoring-preset")?.value || "") {
    const previousRuleset = currentState().project?.scoring?.ruleset;
    if (ruleset !== previousRuleset) scoringPayload.penalty_counts = {};
    await callApi("/api/scoring/profile", { ruleset });
    await callApi("/api/scoring", scoringPayload);
  }

  function scheduleScoringApply() {
    autoApplyScoring({
      scoringPayload: readScoringPayload(),
      ruleset: $("scoring-preset")?.value || "",
    });
  }

  return Object.freeze({
    scoringWorkbenchShown,
    setScoringWorkbenchExpanded,
    renderScoringTable,
    renderScoringTables,
    renderScoringPresetOptions,
    renderScoringPresetDescription,
    renderPractiScoreSummaries,
    readScoringPayload,
    applyScoringSettings,
    scheduleScoringApply,
  });
}
