export function createMatchView({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => ({}),
  getCurrentWorkspaceStageId = () => "",
  getStageCompositeClips = () => [],
  setSelectedStageCompositeStageId = () => {},
  syncControlValue = () => {},
  callApi = async () => null,
  refresh = async () => null,
  refreshStageComposite = async () => null,
  ensureCompositeOutputProfile = async () => null,
  renderJsonDetail = () => {},
  fileName = (value) => value || "",
  activity = () => {},
} = {}) {
  const recapPanelState = {
    selectedStageIds: null,
    stageOrder: [],
    stageOptionsById: {},
    transition: "cut",
    resultCard: "none",
    knownStageIds: new Set(),
    statusText: "Ready to render a match recap.",
    resultsText: "",
    resultsHidden: true,
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function stageEntryLabel(entry, index = 0) {
    return entry.display_name || entry.name || entry.stage_id || `Stage ${index + 1}`;
  }

  function stageEntryHasExportableMedia(entry) {
    return entry?.source_media_present !== false && entry?.media_loaded !== false;
  }

  function countStageOverrides(entry) {
    const overrideValues = entry?.override_values || {};
    return entry?.override_count || Object.keys(overrideValues).length;
  }

  function stageStatusLabel(entry) {
    const status = String(entry?.status || "pending").trim().toLowerCase();
    if (!status) return "Pending";
    return status
      .split(/[_\s]+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function stageReadinessLabel(entry) {
    return stageEntryHasExportableMedia(entry) ? "Media ready" : "Media missing";
  }

  function stageInheritanceLabel(entry) {
    const overrideCount = countStageOverrides(entry);
    if (entry?.inherited_from_first) return "Shared from Stage 1";
    if (overrideCount) {
      return `${overrideCount} stage override${overrideCount === 1 ? "" : "s"}`;
    }
    return "Using shared defaults";
  }

  function formatTimestamp(value) {
    if (!value) return "Not reviewed yet";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return String(value);
    }
  }

  function clampAudioGain(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return 1;
    return Math.max(0, Math.min(2, numericValue));
  }

  function formatMetricSummary(entry) {
    const summary = entry?.metric_summary || {};
    const parts = [];
    const score = summary.score ?? summary.score_total;
    if (score !== undefined && score !== null && score !== "") {
      parts.push(`Score ${score}`);
    }
    const hitFactor = summary.hit_factor ?? summary.hitFactor;
    if (hitFactor !== undefined && hitFactor !== null && hitFactor !== "") {
      parts.push(`HF ${hitFactor}`);
    }
    const cumulativeTimeMs = summary.cumulative_time_ms ?? summary.cumulative_time;
    if (cumulativeTimeMs !== undefined && cumulativeTimeMs !== null && cumulativeTimeMs !== "") {
      const numericValue = Number(cumulativeTimeMs);
      if (Number.isFinite(numericValue)) {
        parts.push(`Time ${(numericValue / 1000).toFixed(2)}s`);
      }
    }
    const shotCount = summary.shot_count;
    if (shotCount !== undefined && shotCount !== null && shotCount !== "") {
      const numericShotCount = Number(shotCount);
      const shotLabel = Number.isFinite(numericShotCount) && numericShotCount === 1 ? "shot" : "shots";
      parts.push(`${shotCount} ${shotLabel}`);
    }
    return parts.slice(0, 3);
  }

  function buildStageChips(entry, { showScoreBadges = true } = {}) {
    const chips = [
      {
        label: stageStatusLabel(entry),
        tone: String(entry?.status || "").trim().toLowerCase() === "complete" ? "success" : "neutral",
      },
      {
        label: stageReadinessLabel(entry),
        tone: stageEntryHasExportableMedia(entry) ? "success" : "warning",
      },
    ];
    const overrideCount = countStageOverrides(entry);
    if (overrideCount) {
      chips.push({
        label: `${overrideCount} override${overrideCount === 1 ? "" : "s"}`,
        tone: "accent",
      });
    } else {
      chips.push({
        label: entry?.inherited_from_first ? "Shared from Stage 1" : "Shared defaults",
        tone: entry?.inherited_from_first ? "info" : "neutral",
      });
    }
    if (showScoreBadges) {
      const metricSummary = formatMetricSummary(entry);
      if (metricSummary[0]) {
        chips.push({ label: metricSummary[0], tone: "accent" });
      }
    }
    return chips;
  }

  function renderChipList(chips = []) {
    return chips
      .map((chip) => `<span class="match-chip match-chip--${escapeHtml(chip?.tone || "neutral")}">${escapeHtml(chip?.label || "")}</span>`)
      .join("");
  }

  function syncSelectedStageEntry(entries = []) {
    const normalizedEntries = entries.filter((entry) => String(entry?.stage_id || "").trim());
    if (!normalizedEntries.length) {
      setSelectedStageCompositeStageId("");
      return { selectedEntry: null, selectedStageId: "" };
    }

    const currentStageId = String(getCurrentWorkspaceStageId() || "").trim();
    const selectedEntry = normalizedEntries.find((entry) => String(entry?.stage_id || "").trim() === currentStageId)
      || normalizedEntries[0]
      || null;
    const selectedStageId = String(selectedEntry?.stage_id || "").trim();
    if (selectedStageId && selectedStageId !== currentStageId) {
      setSelectedStageCompositeStageId(selectedStageId);
    }
    return { selectedEntry, selectedStageId };
  }

  function resolveSelectedStageEntry(entries = []) {
    return syncSelectedStageEntry(entries).selectedEntry;
  }

  function navigateToMatchSection(sectionId) {
    if (!sectionId) return;
    documentObject
      .querySelector(`[data-workspace-view="match"][data-workspace-target="${sectionId}"]`)
      ?.click();
  }

  function renderSelectedStagePanels(entries = []) {
    const detailPanel = $("match-stage-detail-panel");
    const detailStatus = $("match-stage-detail-status");
    const workflowPanel = $("match-stage-workflow-panel");
    const workflowStatus = $("match-stage-workflow-status");
    const workspace = getState()?.workspace || {};
    const showScoreBadges = $("match-setting-show-score")?.checked ?? true;
    const selectedEntry = resolveSelectedStageEntry(entries);
    const readyCount = entries.filter((entry) => stageEntryHasExportableMedia(entry)).length;
    const customCount = entries.filter((entry) => {
      const overrideValues = entry?.override_values || {};
      return Boolean(entry?.override_count || Object.keys(overrideValues).length);
    }).length;

    if (!entries.length) {
      if (detailStatus) detailStatus.textContent = "Select a stage to inspect it.";
      if (detailPanel) detailPanel.textContent = "Select a stage to inspect it.";
      if (workflowStatus) workflowStatus.textContent = "Open or create a workspace to continue.";
      if (workflowPanel) workflowPanel.textContent = "Open or create a workspace to manage stage workflow.";
      return;
    }

    detailPanel?.classList.add("match-context-panel");
    workflowPanel?.classList.add("match-context-panel");

    const selectedLabel = stageEntryLabel(selectedEntry, selectedEntry?.order_index ? selectedEntry.order_index - 1 : 0);
    const overrideCount = countStageOverrides(selectedEntry);
    const mediaText = stageEntryHasExportableMedia(selectedEntry) ? "Ready for Stage edit and export" : "Media still missing";
    const inheritanceText = stageInheritanceLabel(selectedEntry);
    const metricSummary = formatMetricSummary(selectedEntry);
    const activeMatchSection = documentObject.querySelector('[data-workspace-view="match"].active')?.dataset.workspaceTarget || "match-section-stages";
    const workflowSections = [
      {
        id: "match-section-defaults",
        label: "Defaults",
        description: "Shared framing, overlay data, title, and logo.",
      },
      {
        id: "match-section-overrides",
        label: "Overrides",
        description: "Per-stage changes without losing the shared setup.",
      },
      {
        id: "match-section-recap",
        label: "Recap",
        description: "Order stages, set subtitles, and tune recap audio.",
      },
      {
        id: "match-section-composite",
        label: "Composite",
        description: "Refine the selected stage with Compose clips and cut overrides.",
      },
      {
        id: "match-section-export",
        label: "Export",
        description: "Batch output the match with the current queue and recipe.",
      },
    ];

    if (detailStatus) detailStatus.textContent = `${selectedLabel} • ${mediaText}`;
    if (detailPanel) {
      detailPanel.innerHTML = `
        <div class="match-context-hero">
          <div class="match-context-copy">
            <p class="eyebrow">Selected Stage</p>
            <h4>${escapeHtml(selectedLabel)}</h4>
            <p class="match-context-subtitle">${escapeHtml(selectedEntry?.stage_id || "")}</p>
          </div>
          <div class="workspace-context-badges">
            ${renderChipList(buildStageChips(selectedEntry, { showScoreBadges }))}
          </div>
        </div>
        <div class="match-stage-stat-grid match-stage-stat-grid-detail">
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Stage order</span>
            <strong class="match-stage-stat-value">${escapeHtml(selectedEntry?.stage_number || selectedEntry?.order_index || "--")}</strong>
          </article>
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Overrides</span>
            <strong class="match-stage-stat-value">${escapeHtml(overrideCount ? `${overrideCount} custom` : "Inherited")}</strong>
          </article>
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Review</span>
            <strong class="match-stage-stat-value">${escapeHtml(selectedEntry?.last_reviewed_at ? formatTimestamp(selectedEntry.last_reviewed_at) : "Not reviewed yet")}</strong>
          </article>
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Workspace</span>
            <strong class="match-stage-stat-value">${escapeHtml(workspace?.name || "Untitled Match")}</strong>
          </article>
        </div>
        ${metricSummary.length ? `
          <p class="hint match-context-note">${escapeHtml(metricSummary.join(" • "))}</p>
        ` : `
          <p class="hint match-context-note">${escapeHtml(inheritanceText)}. ${escapeHtml(mediaText)}.</p>
        `}
        <div class="workspace-inline-actions">
          <button class="match-action-button" type="button" data-selected-stage-action="open">Open In Stage</button>
          <button class="match-action-button" type="button" data-selected-stage-action="remove">Remove Stage</button>
          <button class="match-action-button" type="button" data-selected-stage-action="reset" ${overrideCount ? "" : "disabled"}>Reset Override</button>
        </div>
      `;

      detailPanel.querySelector('[data-selected-stage-action="open"]')?.addEventListener("click", async () => {
        await callApi("/api/workspace/stage/open", { stage_id: selectedEntry.stage_id });
        windowObject.setActiveSurface?.("single");
      });
      detailPanel.querySelector('[data-selected-stage-action="remove"]')?.addEventListener("click", async () => {
        if (!windowObject.confirm("Remove this stage from the match?")) return;
        await callApi("/api/workspace/stage/remove", { stage_id: selectedEntry.stage_id });
        await refresh();
      });
      detailPanel.querySelector('[data-selected-stage-action="reset"]')?.addEventListener("click", async () => {
        await callApi("/api/workspace/stage/override/reset", { stage_id: selectedEntry.stage_id });
        await refresh();
      });
    }

    if (workflowStatus) {
      workflowStatus.textContent = `${entries.length} stage(s) • ${readyCount} ready • ${customCount} customized`;
    }
    if (workflowPanel) {
      workflowPanel.innerHTML = `
        <div class="match-context-hero">
          <div class="match-context-copy">
            <p class="eyebrow">Match Workflow</p>
            <h4>${escapeHtml(workspace?.name || "Untitled Match")}</h4>
            <p class="match-context-subtitle">Selected stage: ${escapeHtml(selectedLabel)}</p>
          </div>
          <div class="workspace-context-badges">
            ${renderChipList([
              { label: `${entries.length} total`, tone: "neutral" },
              { label: `${readyCount} ready`, tone: "success" },
              { label: `${customCount} custom`, tone: "accent" },
            ])}
          </div>
        </div>
        <div class="match-workflow-shortcuts">
          ${workflowSections.map((section) => `
            <button
              class="match-workflow-shortcut${section.id === activeMatchSection ? " active" : ""}"
              type="button"
              data-workflow-target="${escapeHtml(section.id)}"
            >
              <strong>${escapeHtml(section.label)}</strong>
              <span>${escapeHtml(section.description)}</span>
            </button>
          `).join("")}
        </div>
        <div class="match-stage-stat-grid match-stage-stat-grid-detail">
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Workspace path</span>
            <strong class="match-stage-stat-value">${escapeHtml(workspace?.path || "No workspace path saved")}</strong>
          </article>
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Updated</span>
            <strong class="match-stage-stat-value">${escapeHtml(formatTimestamp(workspace?.updated_at))}</strong>
          </article>
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Selected stage</span>
            <strong class="match-stage-stat-value">${escapeHtml(selectedEntry?.stage_id || "--")}</strong>
          </article>
          <article class="match-stage-stat">
            <span class="match-stage-stat-label">Current focus</span>
            <strong class="match-stage-stat-value">${escapeHtml(mediaText)}</strong>
          </article>
        </div>
        <div class="workspace-inline-actions">
          <button class="match-action-button" type="button" data-workflow-action="open">Open Selected Stage</button>
          <button class="match-action-button" type="button" data-workflow-action="reset" ${overrideCount ? "" : "disabled"}>Reset Selected Override</button>
        </div>
        <p class="hint workspace-panel-note">The selected stage stays pinned while you move between defaults, overrides, recap, composite, and export.</p>
      `;
      workflowPanel.querySelectorAll("[data-workflow-target]").forEach((button) => {
        button.addEventListener("click", () => navigateToMatchSection(button.dataset.workflowTarget || ""));
      });
      workflowPanel.querySelector('[data-workflow-action="open"]')?.addEventListener("click", async () => {
        await callApi("/api/workspace/stage/open", { stage_id: selectedEntry.stage_id });
        windowObject.setActiveSurface?.("single");
      });
      workflowPanel.querySelector('[data-workflow-action="reset"]')?.addEventListener("click", async () => {
        await callApi("/api/workspace/stage/override/reset", { stage_id: selectedEntry.stage_id });
        await refresh();
      });
    }
  }

  function checkSetupOnceBanner() {
    const banner = $("setup-once-banner");
    if (!banner) return;
    const stages = getState()?.workspace_stage_entries || [];
    const firstStage = stages[0] || null;
    const firstStageNamed = Boolean(firstStage?.display_name || firstStage?.name || firstStage?.stage_id);
    const firstStageReady = firstStage?.source_media_present !== false && firstStage?.media_loaded !== false;
    banner.hidden = !(stages.length > 1 && firstStageNamed && firstStageReady);
  }

  function syncRecapPanelState(entries = []) {
    const stageIds = entries
      .map((entry) => String(entry?.stage_id || "").trim())
      .filter(Boolean);
    const stageIdSet = new Set(stageIds);
    const knownStageIds = recapPanelState.knownStageIds;
    const currentSelection = recapPanelState.selectedStageIds;
    if (!(currentSelection instanceof Set) || knownStageIds.size === 0) {
      recapPanelState.selectedStageIds = new Set(stageIds);
    } else {
      const overlappingStageIds = stageIds.filter((stageId) => knownStageIds.has(stageId));
      if (currentSelection.size > 0 && overlappingStageIds.length === 0) {
        recapPanelState.selectedStageIds = new Set(stageIds);
      } else {
        recapPanelState.selectedStageIds = new Set(
          [...currentSelection].filter((stageId) => stageIdSet.has(stageId)),
        );
      }
    }

    const preservedStageOrder = Array.isArray(recapPanelState.stageOrder)
      ? recapPanelState.stageOrder.filter((stageId) => stageIdSet.has(stageId))
      : [];
    const appendedStageOrder = stageIds.filter((stageId) => !preservedStageOrder.includes(stageId));
    recapPanelState.stageOrder = [...preservedStageOrder, ...appendedStageOrder];

    const previousOptions = recapPanelState.stageOptionsById || {};
    recapPanelState.stageOptionsById = Object.fromEntries(
      recapPanelState.stageOrder.map((stageId) => {
        const stageOption = previousOptions[stageId] || {};
        return [
          stageId,
          {
            subtitle: String(stageOption.subtitle || ""),
            audioGain: clampAudioGain(stageOption.audioGain ?? 1),
            audioMuted: Boolean(stageOption.audioMuted ?? false),
          },
        ];
      }),
    );

    recapPanelState.knownStageIds = stageIdSet;
  }

  function moveRecapStage(stageId, targetIndex) {
    const currentOrder = Array.isArray(recapPanelState.stageOrder) ? [...recapPanelState.stageOrder] : [];
    const currentIndex = currentOrder.indexOf(stageId);
    if (currentIndex === -1) return;
    const [movingStageId] = currentOrder.splice(currentIndex, 1);
    const boundedIndex = Math.max(0, Math.min(currentOrder.length, Number(targetIndex) || 0));
    currentOrder.splice(boundedIndex, 0, movingStageId);
    recapPanelState.stageOrder = currentOrder;
    activity("ui.match.recap.reorder", { stageId, targetIndex: boundedIndex });
  }

  function orderedRecapStageIds() {
    return Array.isArray(recapPanelState.stageOrder)
      ? recapPanelState.stageOrder.filter(Boolean)
      : [];
  }

  function captureRecapPanelSelection(recap = $("match-recap-panel")) {
    if (!recap) return [];
    const selected = [...recap.querySelectorAll(".recap-stage-check:checked")]
      .map((checkbox) => String(checkbox.dataset.stageId || "").trim())
      .filter(Boolean);
    recapPanelState.selectedStageIds = new Set(selected);
    return selected;
  }

  function updateRecapStageOption(stageId, patch = {}) {
    const currentOption = recapPanelState.stageOptionsById?.[stageId] || {};
    recapPanelState.stageOptionsById = {
      ...(recapPanelState.stageOptionsById || {}),
      [stageId]: {
        subtitle: String(currentOption.subtitle || ""),
        audioGain: clampAudioGain(currentOption.audioGain ?? 1),
        audioMuted: Boolean(currentOption.audioMuted ?? false),
        ...patch,
      },
    };
  }

  function renderRecapPanel(entries = []) {
    const recap = $("match-recap-panel");
    if (!recap) return;
    if (!entries.length) {
      recap.innerHTML = '<p class="hint">Create or open a workspace to build a Match Recap.</p>';
      recapPanelState.selectedStageIds = null;
      recapPanelState.knownStageIds = new Set();
      return;
    }

    syncRecapPanelState(entries);
    recap.classList.add("match-recap-detail");

    const orderedEntries = orderedRecapStageIds()
      .map((stageId) => entries.find((entry) => String(entry?.stage_id || "").trim() === stageId))
      .filter(Boolean);
    const selectedCount = orderedEntries.filter((entry) => recapPanelState.selectedStageIds?.has(String(entry?.stage_id || "").trim())).length;

    recap.innerHTML = `
      <div class="match-recap-shell">
        <div class="match-recap-header">
          <div>
            <strong>Match Recap</strong>
            <p class="hint">Select stages, drag to reorder them, and tune subtitle/audio per stage for this recap.</p>
          </div>
          <div class="workspace-context-badges">
            <span class="workspace-summary-pill">${selectedCount} selected</span>
            <span class="workspace-summary-pill">${orderedEntries.length} total</span>
          </div>
        </div>
        <div class="match-recap-toolbar">
          <div class="workspace-inline-actions">
            <button id="recap-select-all" class="match-action-button" type="button">Select All</button>
            <button id="recap-select-none" class="match-action-button" type="button">Select None</button>
          </div>
          <span class="hint">Drag a stage row to reorder the recap. Subtitle and audio settings apply only to this render.</span>
        </div>
        <div id="match-recap-stage-list" class="match-recap-stage-list">
          ${orderedEntries.map((entry, index) => {
            const stageId = String(entry?.stage_id || "").trim();
            const stageOption = recapPanelState.stageOptionsById?.[stageId] || {};
            const selected = recapPanelState.selectedStageIds?.has(stageId);
            const stageMeta = [
              `Stage ${entry?.stage_number || entry?.order_index || index + 1}`,
              stageReadinessLabel(entry),
              stageInheritanceLabel(entry),
            ];
            return `
              <article class="match-recap-stage-row${selected ? " selected" : " excluded"}" data-stage-id="${escapeHtml(stageId)}" draggable="true">
                <div class="match-recap-stage-main">
                  <span class="match-recap-stage-handle" aria-hidden="true">⋮⋮</span>
                  <label class="match-recap-stage-toggle">
                    <input type="checkbox" class="recap-stage-check" data-stage-id="${escapeHtml(stageId)}" ${selected ? "checked" : ""} />
                    <span class="match-recap-stage-copy">
                      <strong>${index + 1}. ${escapeHtml(stageEntryLabel(entry, index))}</strong>
                      <small>${escapeHtml(stageMeta.join(" • "))}</small>
                    </span>
                  </label>
                  <div class="match-recap-stage-reorder">
                    <button type="button" class="match-stage-action" data-stage-move="up" data-stage-id="${escapeHtml(stageId)}" ${index === 0 ? "disabled" : ""}>↑</button>
                    <button type="button" class="match-stage-action" data-stage-move="down" data-stage-id="${escapeHtml(stageId)}" ${index === orderedEntries.length - 1 ? "disabled" : ""}>↓</button>
                  </div>
                </div>
                <div class="match-recap-stage-fields">
                  <label>Subtitle
                    <input
                      type="text"
                      class="recap-stage-subtitle"
                      data-stage-id="${escapeHtml(stageId)}"
                      value="${escapeHtml(stageOption.subtitle || "")}"
                      placeholder="Optional on-screen stage subtitle"
                    />
                  </label>
                  <label>Gain
                    <input
                      type="number"
                      min="0"
                      max="2"
                      step="0.05"
                      class="recap-stage-gain"
                      data-stage-id="${escapeHtml(stageId)}"
                      value="${clampAudioGain(stageOption.audioGain ?? 1).toFixed(2)}"
                    />
                  </label>
                  <label class="check-row">
                    <input type="checkbox" class="recap-stage-mute" data-stage-id="${escapeHtml(stageId)}" ${stageOption.audioMuted ? "checked" : ""} />
                    Mute audio
                  </label>
                </div>
              </article>
            `;
          }).join("")}
        </div>
        <div class="match-recap-controls">
          <div class="control-grid">
            <label>Transition
              <select id="recap-transition">
                <option value="cut">Cut</option>
                <option value="fade">Fade</option>
                <option value="dissolve">Dissolve</option>
              </select>
            </label>
            <label>Result Card
              <select id="recap-result-card">
                <option value="none">None</option>
                <option value="end">At End</option>
                <option value="each">Per Stage</option>
              </select>
            </label>
          </div>
          <button id="recap-render" class="match-action-button" type="button">Render Recap</button>
        </div>
        <div id="recap-progress" hidden>
          <div class="progress-bar">
            <div class="progress-fill"></div>
          </div>
        </div>
        <p id="recap-status" class="hint" aria-live="polite">Ready to render a match recap.</p>
        <pre id="recap-results" class="automation-detail" hidden></pre>
      </div>
    `;

    syncControlValue($("recap-transition"), recapPanelState.transition || "cut");
    syncControlValue($("recap-result-card"), recapPanelState.resultCard || "none");
    const recapStatus = $("recap-status");
    if (recapStatus) recapStatus.textContent = recapPanelState.statusText;
    const recapResults = $("recap-results");
    if (recapResults) {
      recapResults.hidden = recapPanelState.resultsHidden;
      recapResults.textContent = recapPanelState.resultsText;
    }

    $("recap-select-all")?.addEventListener("click", () => {
      recapPanelState.selectedStageIds = new Set(orderedEntries.map((entry) => String(entry?.stage_id || "").trim()).filter(Boolean));
      renderRecapPanel(entries);
    });
    $("recap-select-none")?.addEventListener("click", () => {
      recapPanelState.selectedStageIds = new Set();
      renderRecapPanel(entries);
    });

    recap.querySelectorAll(".recap-stage-check").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        captureRecapPanelSelection(recap);
        renderRecapPanel(entries);
      });
    });
    recap.querySelectorAll(".recap-stage-subtitle").forEach((input) => {
      input.addEventListener("input", (event) => {
        const stageId = String(event?.target?.dataset?.stageId || "").trim();
        if (!stageId) return;
        updateRecapStageOption(stageId, { subtitle: String(event?.target?.value || "") });
      });
    });
    recap.querySelectorAll(".recap-stage-gain").forEach((input) => {
      input.addEventListener("change", (event) => {
        const stageId = String(event?.target?.dataset?.stageId || "").trim();
        if (!stageId) return;
        const audioGain = clampAudioGain(event?.target?.value ?? 1);
        updateRecapStageOption(stageId, { audioGain });
        event.target.value = audioGain.toFixed(2);
      });
    });
    recap.querySelectorAll(".recap-stage-mute").forEach((input) => {
      input.addEventListener("change", (event) => {
        const stageId = String(event?.target?.dataset?.stageId || "").trim();
        if (!stageId) return;
        updateRecapStageOption(stageId, { audioMuted: Boolean(event?.target?.checked) });
      });
    });
    recap.querySelectorAll("[data-stage-move]").forEach((button) => {
      button.addEventListener("click", () => {
        const stageId = String(button.dataset.stageId || "").trim();
        if (!stageId) return;
        const orderedStageIds = orderedRecapStageIds();
        const currentIndex = orderedStageIds.indexOf(stageId);
        if (currentIndex === -1) return;
        moveRecapStage(stageId, button.dataset.stageMove === "up" ? currentIndex - 1 : currentIndex + 1);
        renderRecapPanel(entries);
      });
    });
    recap.querySelectorAll(".match-recap-stage-row").forEach((row, index) => {
      row.addEventListener("dragstart", (event) => {
        row.classList.add("dragging");
        event.dataTransfer?.setData("text/plain", String(row.dataset.stageId || ""));
      });
      row.addEventListener("dragend", () => {
        row.classList.remove("dragging");
        recap.querySelectorAll(".match-recap-stage-row").forEach((candidate) => candidate.classList.remove("drag-over"));
      });
      row.addEventListener("dragover", (event) => {
        event.preventDefault();
        row.classList.add("drag-over");
      });
      row.addEventListener("dragleave", () => {
        row.classList.remove("drag-over");
      });
      row.addEventListener("drop", (event) => {
        event.preventDefault();
        row.classList.remove("drag-over");
        const draggedStageId = String(event.dataTransfer?.getData("text/plain") || "").trim();
        if (!draggedStageId || draggedStageId === row.dataset.stageId) return;
        moveRecapStage(draggedStageId, index);
        renderRecapPanel(entries);
      });
    });
    $("recap-transition")?.addEventListener("change", (event) => {
      recapPanelState.transition = event?.target?.value || "cut";
    });
    $("recap-result-card")?.addEventListener("change", (event) => {
      recapPanelState.resultCard = event?.target?.value || "none";
    });

    $("recap-render")?.addEventListener("click", async () => {
      const recapElements = () => {
        const progress = $("recap-progress");
        return {
          progress,
          fill: progress?.querySelector(".progress-fill"),
          status: $("recap-status"),
          results: $("recap-results"),
        };
      };
      captureRecapPanelSelection(recap);
      const selected = orderedRecapStageIds().filter((stageId) => recapPanelState.selectedStageIds?.has(stageId));
      recapPanelState.transition = $("recap-transition")?.value || recapPanelState.transition || "cut";
      recapPanelState.resultCard = $("recap-result-card")?.value || recapPanelState.resultCard || "none";
      let { progress, fill, status, results } = recapElements();
      if (!selected.length) {
        recapPanelState.statusText = "Select at least one stage for the recap.";
        recapPanelState.resultsText = "";
        recapPanelState.resultsHidden = true;
        if (progress) progress.hidden = true;
        if (fill) fill.style.width = "0%";
        if (status) status.textContent = recapPanelState.statusText;
        if (results) {
          results.hidden = true;
          results.textContent = "";
        }
        return;
      }
      recapPanelState.statusText = `Rendering recap for ${selected.length} stage(s)...`;
      recapPanelState.resultsText = "";
      recapPanelState.resultsHidden = true;
      if (progress) progress.hidden = false;
      if (fill) fill.style.width = "35%";
      if (status) status.textContent = recapPanelState.statusText;
      if (results) {
        results.hidden = true;
        results.textContent = "";
      }
      const result = await callApi("/api/workspace/recap/render", {
        stage_ids: selected,
        transition: recapPanelState.transition,
        result_card: recapPanelState.resultCard,
        stage_options: selected.map((stageId) => {
          const stageOption = recapPanelState.stageOptionsById?.[stageId] || {};
          return {
            stage_id: stageId,
            subtitle: String(stageOption.subtitle || "").trim(),
            audio_gain: clampAudioGain(stageOption.audioGain ?? 1),
            audio_muted: Boolean(stageOption.audioMuted),
          };
        }),
      });
      ({ progress, fill, status, results } = recapElements());
      if (progress) progress.hidden = true;
      if (fill) fill.style.width = result?.success ? "100%" : "0%";
      if (!result) {
        recapPanelState.statusText = "Recap render failed.";
        recapPanelState.resultsText = "";
        recapPanelState.resultsHidden = true;
        if (status) status.textContent = recapPanelState.statusText;
        return;
      }
      if (result.success) {
        recapPanelState.statusText = `Recap ready: ${result.output_path}`;
      } else {
        recapPanelState.statusText = result.error || "Recap render failed.";
      }
      recapPanelState.resultsText = JSON.stringify(result, null, 2);
      recapPanelState.resultsHidden = false;
      if (status) status.textContent = recapPanelState.statusText;
      if (results) {
        results.hidden = false;
        results.textContent = recapPanelState.resultsText;
      }
    });
  }

  function renderBatchExportQueue(entries = []) {
    const queue = $("batch-export-queue");
    const status = $("batch-export-status");
    const progress = $("batch-export-progress");
    const results = $("batch-export-results");
    if (!queue) return;
    if (progress) progress.hidden = true;
    if (results) {
      results.hidden = true;
      results.textContent = "";
    }
    if (!entries.length) {
      queue.innerHTML = '<p class="hint">Add stages to the workspace to batch export.</p>';
      if (status) status.textContent = "Ready";
      return;
    }

    queue.innerHTML = entries
      .map((entry, index) => {
        const exportable = stageEntryHasExportableMedia(entry);
        const summaryParts = [
          exportable ? "Ready" : "No media",
        ];
        if (entry.override_count || Object.keys(entry.override_values || {}).length) {
          summaryParts.push("Custom");
        }
        if (entry.inherited_from_first) {
          summaryParts.push("Shared");
        }
        return `
          <label class="batch-export-item" data-stage-id="${escapeHtml(entry.stage_id)}">
            <input type="checkbox" ${exportable ? "checked" : "disabled"} />
            <span class="batch-export-copy">
              <strong>${index + 1}. ${escapeHtml(stageEntryLabel(entry, index))}</strong>
              <small>${summaryParts.join(" • ")}</small>
            </span>
          </label>
        `;
      })
      .join("");

    if (status) {
      const exportableCount = entries.filter((entry) => stageEntryHasExportableMedia(entry)).length;
      status.textContent = exportableCount
        ? `${exportableCount} stage(s) ready to export.`
        : "No stages are ready to export.";
    }
  }

  function renderWorkspaceStages() {
    const state = getState();
    const list = $("workspace-stage-list");
    if (!list) return;
    const entries = state?.workspace_stage_entries || [];
    list.classList.add("match-stage-list");
    const previousStageId = String(getCurrentWorkspaceStageId() || "").trim();
    const { selectedStageId } = syncSelectedStageEntry(entries);
    list.innerHTML = "";
    const showScoreBadges = $("match-setting-show-score")?.checked ?? true;
    entries.forEach((entry, index) => {
      const stageId = String(entry?.stage_id || "").trim();
      const overrideCount = countStageOverrides(entry);
      const metricSummary = formatMetricSummary(entry);
      const stageNumber = entry?.stage_number || entry?.order_index || index + 1;
      const card = documentObject.createElement("div");
      card.className = "match-stage-card";
      card.dataset.stageId = stageId;
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", `${stageEntryLabel(entry, index)} match tile`);
      if (stageId === selectedStageId) card.classList.add("selected");

      card.innerHTML = `
        <div class="match-stage-preview${entry?.preview_url ? " has-preview" : entry?.thumbnail_path ? " has-thumbnail" : ""}">
          ${entry?.preview_url ? `<video class="match-stage-preview-video" src="${escapeHtml(entry.preview_url)}" muted playsinline loop autoplay preload="metadata"></video>` : ""}
          <div class="match-stage-preview-header">
            <span class="match-stage-order-pill">Stage ${escapeHtml(stageNumber)}</span>
            <span class="match-stage-preview-state">${escapeHtml(stageStatusLabel(entry))}</span>
          </div>
          <div class="match-stage-preview-copy">
            <strong>${escapeHtml(stageEntryHasExportableMedia(entry) ? "Ready for Stage Edit" : "Needs media before edit")}</strong>
            <span>${escapeHtml(stageInheritanceLabel(entry))}</span>
          </div>
          <div class="match-stage-preview-footer">
            ${renderChipList(buildStageChips(entry, { showScoreBadges }))}
          </div>
        </div>
        <div class="match-stage-body">
          <div class="match-stage-heading">
            <div>
              <h4 class="match-stage-name">${escapeHtml(stageEntryLabel(entry, index))}</h4>
              <p class="match-stage-id">${escapeHtml(entry?.stage_id || "")}</p>
            </div>
          </div>
          <div class="match-stage-stat-grid">
            <article class="match-stage-stat">
              <span class="match-stage-stat-label">Review</span>
              <strong class="match-stage-stat-value">${escapeHtml(entry?.last_reviewed_at ? formatTimestamp(entry.last_reviewed_at) : "Not reviewed")}</strong>
            </article>
            <article class="match-stage-stat">
              <span class="match-stage-stat-label">Overrides</span>
              <strong class="match-stage-stat-value">${escapeHtml(overrideCount ? `${overrideCount} custom` : "Inherited")}</strong>
            </article>
            <article class="match-stage-stat">
              <span class="match-stage-stat-label">Media</span>
              <strong class="match-stage-stat-value">${escapeHtml(stageReadinessLabel(entry))}</strong>
            </article>
            <article class="match-stage-stat">
              <span class="match-stage-stat-label">Focus</span>
              <strong class="match-stage-stat-value">${escapeHtml(metricSummary[1] || metricSummary[0] || "Stage workflow")}</strong>
            </article>
          </div>
        </div>
      `;

      const preview = card.querySelector(".match-stage-preview");
      if (preview && entry?.thumbnail_path && !entry?.preview_url) {
        preview.style.backgroundImage = `linear-gradient(180deg, rgba(10, 12, 15, 0.12), rgba(10, 12, 15, 0.82)), url(${JSON.stringify(String(entry.thumbnail_path))})`;
      }
      const previewVideo = card.querySelector(".match-stage-preview-video");
      if (previewVideo) {
        previewVideo.defaultMuted = true;
        previewVideo.muted = true;
        previewVideo.playsInline = true;
        previewVideo.addEventListener("canplay", () => {
          const playAttempt = previewVideo.play?.();
          playAttempt?.catch?.(() => {});
        }, { once: true });
      }

      const actions = documentObject.createElement("div");
      actions.className = "match-stage-actions";

      const openBtn = documentObject.createElement("button");
      openBtn.className = "match-stage-action";
      openBtn.type = "button";
      openBtn.textContent = "Open";
      openBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        setSelectedStageCompositeStageId(entry.stage_id);
        await callApi("/api/workspace/stage/open", { stage_id: entry.stage_id });
        windowObject.setActiveSurface?.("single");
      });

      const removeBtn = documentObject.createElement("button");
      removeBtn.className = "match-stage-action";
      removeBtn.type = "button";
      removeBtn.textContent = "Remove";
      removeBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!windowObject.confirm("Remove this stage from the match?")) return;
        await callApi("/api/workspace/stage/remove", { stage_id: entry.stage_id });
        await refresh();
      });

      const resetBtn = documentObject.createElement("button");
      resetBtn.className = "match-stage-action";
      resetBtn.type = "button";
      resetBtn.textContent = "Reset";
      resetBtn.disabled = !overrideCount;
      resetBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await callApi("/api/workspace/stage/override/reset", { stage_id: entry.stage_id });
        await refresh();
      });

      actions.append(openBtn, removeBtn, resetBtn);
      card.append(actions);
      const selectCard = () => {
        list.querySelectorAll(".match-stage-card").forEach((candidate) => candidate.classList.remove("selected"));
        card.classList.add("selected");
        setSelectedStageCompositeStageId(entry.stage_id);
        renderSelectedStagePanels(entries);
        void refreshStageComposite(entry.stage_id);
      };
      card.addEventListener("click", selectCard);
      card.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        selectCard();
      });
      list.append(card);
    });

    if (selectedStageId && selectedStageId !== previousStageId) {
      void refreshStageComposite(selectedStageId);
    }

    checkSetupOnceBanner();
    renderSelectedStagePanels(entries);
    renderRecapPanel(entries);
    renderBatchExportQueue(entries);

    const sharedDefaults = state?.workspace_shared_defaults || {};
    syncControlValue($("shared-frame-profile"), sharedDefaults.frame_profile || "source");
    syncControlValue(
      $("shared-metric-captions"),
      sharedDefaults.metric_caption_preset || sharedDefaults.metric_captions || "none",
    );
    syncControlValue($("shared-lead-in"), sharedDefaults.lead_in_card || "none");
    syncControlValue($("shared-brand-mark"), sharedDefaults.brand_mark || "none");

    const overrideEditor = $("stage-override-editor");
    const overrideGrids = overrideEditor?.querySelectorAll(".control-grid");
    const overrideButton = $("override-apply");
    if (overrideEditor && entries.length && getCurrentWorkspaceStageId()) {
      const activeEntry = entries.find((candidate) => candidate.stage_id === getCurrentWorkspaceStageId());
      const overrides = activeEntry?.override_values || state?.workspace_override_summary?.[getCurrentWorkspaceStageId()] || {};
      overrideEditor.querySelector("p")?.setAttribute("hidden", "");
      overrideGrids?.forEach((grid) => grid.removeAttribute("hidden"));
      if (overrideButton) overrideButton.removeAttribute("hidden");
      syncControlValue($("override-frame-profile"), overrides.frame_profile || "");
      syncControlValue(
        $("override-metric-captions"),
        overrides.metric_caption_preset || overrides.metric_captions || "",
      );
    } else if (overrideEditor) {
      const hint = overrideEditor.querySelector("p");
      if (hint) hint.removeAttribute("hidden");
      overrideGrids?.forEach((grid) => grid.setAttribute("hidden", ""));
      if (overrideButton) overrideButton.setAttribute("hidden", "");
    }

    const emptyState = documentObject.querySelector(".match-empty-state");
    const reviewGrid = documentObject.querySelector("#view-match .match-review-grid");
    const matchSidebar = documentObject.querySelector("#view-match .workspace-sidebar");
    const matchTitle = $("match-workspace-title");
    const matchStatus = $("match-workspace-status");
    const hasWorkspace = Boolean(state?.workspace || state?.workspace_stage_entries?.length);
    const hasStages = entries.length > 0;
    const saveButton = $("workspace-save");
    const readyCount = entries.filter((entry) => stageEntryHasExportableMedia(entry)).length;
    const customCount = entries.filter((entry) => {
      const overrideValues = entry?.override_values || {};
      return Boolean(entry?.override_count || Object.keys(overrideValues).length);
    }).length;
    if (emptyState) emptyState.hidden = hasWorkspace;
    if (reviewGrid) reviewGrid.hidden = !hasWorkspace;
    if (matchSidebar) matchSidebar.hidden = false;
    if (saveButton) saveButton.disabled = !hasWorkspace;
    if (matchTitle) {
      matchTitle.textContent = hasWorkspace
        ? (state?.workspace?.name || "Untitled Match")
        : "No Match Open";
    }
    if (matchStatus) {
      matchStatus.textContent = hasWorkspace
        ? `${entries.length} stage(s) • ${readyCount} ready • ${customCount} customized`
        : "Create or open a workspace to start organizing stages.";
    }
    if (!hasStages && hasWorkspace && list.children.length === 0) {
      list.innerHTML = '<p class="hint" style="padding:12px">No stages yet. Add your first stage.</p>';
    }
  }

  function renderStageComposite() {
    const list = $("stage-composite-list");
    if (!list) return;
    list.innerHTML = "";
    const stageId = getCurrentWorkspaceStageId();
    if (!stageId) {
      list.innerHTML = '<div class="hint">Select a workspace stage to edit Stage Composite clips.</div>';
      return;
    }
    const clips = getStageCompositeClips();
    if (!clips.length) list.innerHTML = '<div class="hint">No clips loaded for this stage.</div>';
    const refreshPlanDetail = async (outputId = "") => {
      const ensuredOutputId = outputId || await ensureCompositeOutputProfile(stageId);
      if (!ensuredOutputId) return null;
      const plan = await callApi("/api/angle/director/plan", {
        stage_id: stageId,
        output_id: ensuredOutputId,
      });
      renderJsonDetail("output-profile-detail", plan);
      return plan;
    };
    const reorderClip = async (clipId, targetIndex) => {
      const result = await callApi("/api/workspace/stage/clip/reorder", {
        stage_id: stageId,
        clip_id: clipId,
        target_index: targetIndex,
      });
      if (result?.success) {
        await refreshStageComposite(stageId);
      }
    };

    clips.forEach((clip, index) => {
      const row = documentObject.createElement("div");
      row.className = "automation-row";
      row.dataset.clipId = clip.clip_id;
      row.draggable = true;
      const summary = documentObject.createElement("div");
      summary.innerHTML = `<strong>${index + 1}. ${fileName(clip.source_path || clip.clip_id)}</strong><br><small>${clip.angle_role || "primary"} • sync ${clip.sync_offset_ms || 0} ms • audio ${clip.audio_muted ? "muted" : clip.audio_gain ?? 1}${clip.audio_primary ? " • primary" : ""}</small>`;
      summary.title = "Drag to reorder this stage composite clip.";
      const actions = documentObject.createElement("div");
      actions.className = "automation-row-actions";
      const moveUp = documentObject.createElement("button");
      moveUp.type = "button";
      moveUp.textContent = "↑";
      moveUp.disabled = index === 0;
      moveUp.title = "Move this clip earlier in the composite order.";
      moveUp.addEventListener("click", async () => {
        await reorderClip(clip.clip_id, index - 1);
      });
      const moveDown = documentObject.createElement("button");
      moveDown.type = "button";
      moveDown.textContent = "↓";
      moveDown.disabled = index === clips.length - 1;
      moveDown.title = "Move this clip later in the composite order.";
      moveDown.addEventListener("click", async () => {
        await reorderClip(clip.clip_id, index + 1);
      });
      const align = documentObject.createElement("button");
      align.type = "button";
      align.textContent = "Angle Align";
      align.addEventListener("click", async () => {
        await callApi("/api/angle/align", { stage_id: stageId, reference_clip_id: clip.clip_id });
        await refreshStageComposite(stageId);
      });
      const planButton = documentObject.createElement("button");
      planButton.type = "button";
      planButton.textContent = "Plan";
      planButton.addEventListener("click", async () => {
        await refreshPlanDetail();
      });
      const remove = documentObject.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove";
      remove.addEventListener("click", async () => {
        await callApi("/api/workspace/stage/clip/remove", { stage_id: stageId, clip_id: clip.clip_id });
        await refreshStageComposite(stageId);
      });

      const editor = documentObject.createElement("div");
      editor.className = "control-grid";
      editor.style.gridColumn = "1 / -1";

      const roleLabel = documentObject.createElement("label");
      roleLabel.innerHTML = `Role
        <select>
          <option value="primary">Primary</option>
          <option value="follow">Follow</option>
          <option value="static">Static</option>
          <option value="detail">Detail</option>
        </select>`;
      const roleSelect = roleLabel.querySelector("select");
      syncControlValue(roleSelect, clip.angle_role || "primary");
      roleSelect?.addEventListener("change", async () => {
        await callApi("/api/workspace/stage/clip/update", {
          stage_id: stageId,
          clip_id: clip.clip_id,
          angle_role: roleSelect.value,
        });
        await refreshStageComposite(stageId);
      });

      const syncLabel = documentObject.createElement("label");
      syncLabel.innerHTML = `Sync offset (ms) <input type="number" step="1" value="${Number(clip.sync_offset_ms || 0)}" />`;
      const syncInput = syncLabel.querySelector("input");
      syncInput?.addEventListener("change", async () => {
        await callApi("/api/workspace/stage/clip/update", {
          stage_id: stageId,
          clip_id: clip.clip_id,
          sync_offset_ms: Number(syncInput.value || 0),
        });
        await refreshStageComposite(stageId);
      });

      const gainLabel = documentObject.createElement("label");
      gainLabel.innerHTML = `Audio gain <input type="number" min="0" max="2" step="0.05" value="${Number(clip.audio_gain ?? 1).toFixed(2)}" />`;
      const gainInput = gainLabel.querySelector("input");
      gainInput?.addEventListener("change", async () => {
        await callApi("/api/audio/mix", {
          stage_id: stageId,
          clip_id: clip.clip_id,
          gain: Number(gainInput.value || 0),
        });
        await refreshStageComposite(stageId);
      });

      const muteLabel = documentObject.createElement("label");
      muteLabel.className = "check-row";
      muteLabel.innerHTML = `<input type="checkbox" ${clip.audio_muted ? "checked" : ""} /> Mute`;
      const muteInput = muteLabel.querySelector("input");
      muteInput?.addEventListener("change", async () => {
        await callApi("/api/audio/mix", {
          stage_id: stageId,
          clip_id: clip.clip_id,
          muted: Boolean(muteInput.checked),
        });
        await refreshStageComposite(stageId);
      });

      const primaryLabel = documentObject.createElement("label");
      primaryLabel.className = "check-row";
      primaryLabel.innerHTML = `<input type="checkbox" ${clip.audio_primary ? "checked" : ""} /> Primary audio`;
      const primaryInput = primaryLabel.querySelector("input");
      primaryInput?.addEventListener("change", async () => {
        await callApi("/api/audio/mix", {
          stage_id: stageId,
          clip_id: clip.clip_id,
          primary: Boolean(primaryInput.checked),
        });
        await refreshStageComposite(stageId);
      });
      editor.append(roleLabel, syncLabel, gainLabel, muteLabel, primaryLabel);

      const cutEditor = documentObject.createElement("div");
      cutEditor.className = "control-grid";
      cutEditor.style.gridColumn = "1 / -1";

      const cutPositionLabel = documentObject.createElement("label");
      cutPositionLabel.innerHTML = `Cut slot <input type="number" min="0" step="1" value="${index}" />`;
      const cutPositionInput = cutPositionLabel.querySelector("input");

      const cutStartLabel = documentObject.createElement("label");
      cutStartLabel.innerHTML = `Start (ms) <input type="number" min="0" step="25" value="0" />`;
      const cutStartInput = cutStartLabel.querySelector("input");

      const cutDurationLabel = documentObject.createElement("label");
      cutDurationLabel.innerHTML = `Duration (ms) <input type="number" min="0" step="25" value="1000" />`;
      const cutDurationInput = cutDurationLabel.querySelector("input");

      const applyCut = documentObject.createElement("button");
      applyCut.type = "button";
      applyCut.textContent = "Apply Cut";
      applyCut.addEventListener("click", async () => {
        const outputId = await ensureCompositeOutputProfile(stageId);
        if (!outputId) return;
        await callApi("/api/angle/director/override", {
          stage_id: stageId,
          clip_id: clip.clip_id,
          output_id: outputId,
          position: Number(cutPositionInput.value || 0),
          start_ms: Number(cutStartInput.value || 0),
          duration_ms: Number(cutDurationInput.value || 0),
        });
        await refreshPlanDetail(outputId);
      });

      const clearCut = documentObject.createElement("button");
      clearCut.type = "button";
      clearCut.textContent = "Clear Cut";
      clearCut.addEventListener("click", async () => {
        const outputId = await ensureCompositeOutputProfile(stageId);
        if (!outputId) return;
        await callApi("/api/angle/director/override/clear", {
          stage_id: stageId,
          output_id: outputId,
          position: Number(cutPositionInput.value || 0),
        });
        await refreshPlanDetail(outputId);
      });

      cutEditor.append(cutPositionLabel, cutStartLabel, cutDurationLabel, applyCut, clearCut);

      actions.append(moveUp, moveDown, align, planButton, remove);
      row.append(summary, actions, editor, cutEditor);

      row.addEventListener("dragstart", (event) => {
        row.style.opacity = "0.55";
        event.dataTransfer?.setData("text/plain", clip.clip_id);
      });
      row.addEventListener("dragend", () => {
        row.style.opacity = "";
        list.querySelectorAll("[data-clip-id]").forEach((candidate) => {
          candidate.style.outline = "";
        });
      });
      row.addEventListener("dragover", (event) => {
        event.preventDefault();
        row.style.outline = "1px dashed var(--accent)";
      });
      row.addEventListener("dragleave", () => {
        row.style.outline = "";
      });
      row.addEventListener("drop", async (event) => {
        event.preventDefault();
        row.style.outline = "";
        const draggedClipId = event.dataTransfer?.getData("text/plain");
        if (!draggedClipId || draggedClipId === clip.clip_id) return;
        await reorderClip(draggedClipId, index);
      });
      list.append(row);
    });
  }

  function persistMatchSettings() {
    const settings = {
      showScoreBadges: $("match-setting-show-score")?.checked ?? true,
      rememberStageSelection: $("match-setting-remember-stage")?.checked ?? true,
    };
    windowObject.localStorage.setItem("splitshot.match.settings", JSON.stringify(settings));
    activity("ui.match.settings.save", settings);
  }

  function applySavedMatchSettings() {
    try {
      const settings = JSON.parse(windowObject.localStorage.getItem("splitshot.match.settings") || "{}");
      if ($("match-setting-show-score")) $("match-setting-show-score").checked = settings.showScoreBadges ?? true;
      if ($("match-setting-remember-stage")) $("match-setting-remember-stage").checked = settings.rememberStageSelection ?? true;
    } catch {}
  }

  return Object.freeze({
    applySavedMatchSettings,
    checkSetupOnceBanner,
    persistMatchSettings,
    renderStageComposite,
    renderWorkspaceStages,
  });
}
