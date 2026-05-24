export function createLibraryView({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getLibrary = () => ({ stages: [], matches: [] }),
  getSelectedLibraryRecord = () => null,
  setSelectedLibraryRecord = () => {},
  callApi = async () => null,
  renderJsonDetail = () => {},
  activity = () => {},
} = {}) {
  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function currentRecords() {
    const library = getLibrary() || { stages: [], matches: [] };
    return [
      ...(library.stages || []).map((record) => ({ ...record, record_type: "stage" })),
      ...(library.matches || []).map((record) => ({ ...record, record_type: "match" })),
    ];
  }

  function libraryRecordId(record) {
    return record?.library_record_id || record?.stage_id || record?.match_id || "";
  }

  function normalizedDiscipline(record) {
    const raw = String(record?.discipline || "")
      .trim()
      .toLowerCase()
      .replace(/[\s-]+/g, "_");
    if (raw.startsWith("uspsa")) return "uspsa";
    if (raw.startsWith("idpa")) return "idpa";
    return raw;
  }

  function renderLibrarySummaryTiles() {
    const container = $("library-summary-tiles");
    if (!container) return;
    const library = getLibrary() || { stages: [], matches: [] };
    const stageRecords = library.stages || [];
    const matchRecords = library.matches || [];
    const records = currentRecords();
    const totalStages = stageRecords.length;
    const totalMatches = matchRecords.length;
    const personalBest = records.filter((record) => record.score != null).sort((a, b) => (b.score || 0) - (a.score || 0))[0];
    const personalBestVal = personalBest ? `${personalBest.score} (${personalBest.display_name || "--"})` : "--";
    const recentCount = records.filter((record) => {
      if (!record.event_date) return false;
      const recordDate = new Date(record.event_date);
      const monthAgo = new Date();
      monthAgo.setMonth(monthAgo.getMonth() - 1);
      return recordDate >= monthAgo;
    }).length;
    container.innerHTML = `
      <div class="library-tile"><span class="library-tile-value">${totalStages}</span><span class="library-tile-label">Total Stages</span></div>
      <div class="library-tile"><span class="library-tile-value">${totalMatches}</span><span class="library-tile-label">Total Matches</span></div>
      <div class="library-tile"><span class="library-tile-value">${escapeHtml(personalBestVal)}</span><span class="library-tile-label">Personal Best</span></div>
      <div class="library-tile"><span class="library-tile-value">${recentCount}</span><span class="library-tile-label">Recent (30d)</span></div>
    `;
  }

  function renderLibraryTags() {
    const container = $("library-tag-list");
    if (!container) return;
    const tags = getSelectedLibraryRecord()?.tags || [];
    container.innerHTML = tags.map((tag) => `
      <span class="library-tag">
        ${escapeHtml(tag)}
        <span class="tag-remove" data-tag="${escapeHtml(tag)}" title="Remove tag">×</span>
      </span>
    `).join("") || '<span class="hint" style="font-size:0.6875rem">No tags</span>';
  }

  function renderPersonalBests() {
    const container = $("personal-bests-list");
    if (!container) return;
    const records = currentRecords();
    if (records.length === 0) {
      container.innerHTML = '<p class="hint">Add records to see personal bests.</p>';
      return;
    }
    const sorted = [...records].filter((record) => record.score != null).sort((a, b) => b.score - a.score).slice(0, 5);
    container.innerHTML = sorted.map((record, index) => `
      <div class="library-record-row">
        <span class="record-rank">#${index + 1}</span>
        <span class="record-name">${escapeHtml(record.display_name || record.competitor_name || "Unknown")}</span>
        <span class="record-score">${escapeHtml(record.score)}</span>
        <span class="record-discipline">${escapeHtml(record.discipline || "")}</span>
      </div>
    `).join("");
  }

  async function fetchLibraryAnalytics(discipline) {
    try {
      return await callApi("/api/library/analytics/trend", {
        metric_key: "score",
        discipline: discipline || "",
      });
    } catch {
      return null;
    }
  }

  function renderAnalyticsCharts(data) {
    const scoreTrend = Array.isArray(data?.trend_points) ? data.trend_points : [];
    const disciplineBreakdown = Array.isArray(data?.discipline_breakdown) ? data.discipline_breakdown : [];
    const totalRecords = Number(data?.total_records ?? data?.records ?? 0);

    const trendEl = $("analytics-score-trend");
    if (trendEl) {
      if (scoreTrend.length === 0) {
        trendEl.innerHTML = '<p class="hint">Add scored Performance records to see a score trend.</p>';
      } else if (scoreTrend.length < 2) {
        trendEl.innerHTML = '<p class="hint">Add at least one more scored record to compare performance over time.</p>';
      } else {
        const maxScore = Math.max(...scoreTrend.map((entry) => entry.score || 0), 1);
        trendEl.innerHTML = `
          <div class="chart-bar-container" style="display:flex;align-items:flex-end;gap:2px;height:120px;padding:4px">
            ${scoreTrend.map((entry) => {
              const height = Math.round(((entry.score || 0) / maxScore) * 100);
              return `<div class="chart-bar" style="height:${height}%;flex:1;background:var(--surface-2);min-width:8px;position:relative" title="${escapeHtml(entry.date || "")}: ${escapeHtml(entry.score || 0)}">
                <span style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-size:9px;color:var(--muted)">${escapeHtml(entry.score || "")}</span>
              </div>`;
            }).join("")}
          </div>
        `;
      }
    }

    const disciplineEl = $("analytics-discipline-chart");
    if (disciplineEl) {
      if (disciplineBreakdown.length === 0) {
        disciplineEl.innerHTML = '<p class="hint">Add Performance records to see discipline breakdown.</p>';
      } else {
        const maxCount = Math.max(...disciplineBreakdown.map((entry) => entry.count), 1);
        disciplineEl.innerHTML = `
          <div class="discipline-bars">
            ${disciplineBreakdown.map((entry) => `
              <div class="discipline-bar">
                <span class="bar-label">${escapeHtml(String(entry.discipline || "").toUpperCase())}</span>
                <span class="bar-fill" style="width:${Math.round((entry.count / maxCount) * 100)}%">${escapeHtml(entry.count)}</span>
              </div>
            `).join("")}
          </div>
        `;
      }
    }

    const outlierEl = $("analytics-outliers");
    if (outlierEl) {
      if (Array.isArray(data?.outliers) && data.outliers.length > 0) {
        outlierEl.innerHTML = data.outliers.map((entry) => `
          <div class="library-record-row">
            <span class="record-name">${escapeHtml(entry.name || "Unknown")}</span>
            <span class="record-score">${escapeHtml(entry.score)}</span>
            <span class="record-discipline">${escapeHtml(entry.direction === "high" ? "High" : "Low")}</span>
          </div>
        `).join("");
      } else if (totalRecords === 0) {
        outlierEl.innerHTML = '<p class="hint">Add Performance records to see outlier detection.</p>';
      } else if (totalRecords < 4) {
        outlierEl.innerHTML = '<p class="hint">Add more records to surface statistically meaningful outliers.</p>';
      } else {
        outlierEl.innerHTML = '<p class="hint">No significant outliers detected.</p>';
      }
    }
  }

  function renderPerformanceLibrary() {
    renderLibrarySummaryTiles();
    const list = $("library-record-list");
    if (!list) return;
    const filterDiscipline = $("library-filter-discipline")?.value || "";
    const sortBy = $("library-sort")?.value || "event_date";
    const selectedRecordId = libraryRecordId(getSelectedLibraryRecord());
    let filtered = currentRecords();
    if (filterDiscipline) {
      filtered = filtered.filter((record) => normalizedDiscipline(record) === filterDiscipline);
    }
    if (sortBy === "score") filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
    else if (sortBy === "display_name") filtered.sort((a, b) => (a.display_name || "").localeCompare(b.display_name || ""));
    else if (sortBy === "discipline") filtered.sort((a, b) => (a.discipline || "").localeCompare(b.discipline || ""));
    list.innerHTML = "";
    if (!filtered.length) {
      list.innerHTML = '<div class="hint">No performance records yet.</div>';
      renderPersonalBests();
      return;
    }
    filtered.forEach((record) => {
      const id = record.library_record_id || record.stage_id || record.match_id;
      const row = documentObject.createElement("div");
      row.className = "library-record-row";
      row.dataset.recordId = id;
      if (selectedRecordId && id === selectedRecordId) row.classList.add("selected");
      row.innerHTML = `
        <span class="library-record-name">${escapeHtml(record.display_name || id || "Untitled")}</span>
        <span class="library-record-date">${escapeHtml(record.event_date || "--")}</span>
        <span class="library-record-discipline">${escapeHtml(record.discipline || "--")}</span>
        <span class="library-record-score">${escapeHtml(record.score != null ? record.score : "--")}</span>
      `;
      row.addEventListener("click", () => {
        documentObject.querySelectorAll(".library-record-row").forEach((candidate) => candidate.classList.remove("selected"));
        row.classList.add("selected");
        setSelectedLibraryRecord(record);
        renderJsonDetail("library-record-detail", record);
        const tagsEditor = $("library-tags-editor");
        const notesEditor = $("library-notes-editor");
        const recordActions = $("library-record-actions");
        if (tagsEditor) tagsEditor.hidden = false;
        if (notesEditor) notesEditor.hidden = false;
        if (recordActions) recordActions.hidden = false;
        renderLibraryTags();
        const notesText = $("library-notes-text");
        if (notesText) notesText.value = record.notes || "";
      });
      list.appendChild(row);
    });
    renderPersonalBests();

    const selectedRecord = getSelectedLibraryRecord();
    if (selectedRecord && selectedRecordId) {
      const tagsEditor = $("library-tags-editor");
      const notesEditor = $("library-notes-editor");
      const recordActions = $("library-record-actions");
      if (tagsEditor) tagsEditor.hidden = false;
      if (notesEditor) notesEditor.hidden = false;
      if (recordActions) recordActions.hidden = false;
      renderJsonDetail("library-record-detail", selectedRecord);
      renderLibraryTags();
      const notesText = $("library-notes-text");
      if (notesText) notesText.value = selectedRecord.notes || "";
    } else {
      const tagsEditor = $("library-tags-editor");
      const notesEditor = $("library-notes-editor");
      const recordActions = $("library-record-actions");
      if (tagsEditor) tagsEditor.hidden = true;
      if (notesEditor) notesEditor.hidden = true;
      if (recordActions) recordActions.hidden = true;
      renderJsonDetail("library-record-detail", {});
      const notesText = $("library-notes-text");
      if (notesText) notesText.value = "";
    }

    const emptyState = documentObject.querySelector(".library-empty-state");
    const sectionHeader = documentObject.querySelector("#view-library .workspace-action-bar");
    const workspaceSections = documentObject.querySelector("#view-library .workspace-sections");
    const librarySidebar = documentObject.querySelector("#view-library .workspace-sidebar");
    const hasRecords = filtered.length > 0;
    if (emptyState) emptyState.hidden = hasRecords;
    if (sectionHeader) sectionHeader.hidden = !hasRecords;
    if (workspaceSections) workspaceSections.hidden = !hasRecords;
    if (librarySidebar) librarySidebar.hidden = false;
  }

  function addLibraryTag(tag) {
    const record = getSelectedLibraryRecord();
    if (!record) return;
    record.tags = record.tags || [];
    if (!record.tags.includes(tag)) {
      record.tags.push(tag);
      renderLibraryTags();
    }
  }

  function removeLibraryTag(tag) {
    const record = getSelectedLibraryRecord();
    if (!record?.tags) return;
    record.tags = record.tags.filter((candidate) => candidate !== tag);
    renderLibraryTags();
  }

  function saveLibraryNotes(notes) {
    const record = getSelectedLibraryRecord();
    if (!record) return;
    record.notes = notes;
    activity("ui.library.notes.save");
  }

  function persistLibrarySettings() {
    const settings = {
      defaultSort: $("library-setting-default-sort")?.value || "event_date",
      autoRefresh: $("library-setting-auto-refresh")?.checked ?? true,
    };
    windowObject.localStorage.setItem("splitshot.library.settings", JSON.stringify(settings));
    activity("ui.library.settings.save", settings);
  }

  function applySavedLibrarySettings() {
    try {
      const settings = JSON.parse(windowObject.localStorage.getItem("splitshot.library.settings") || "{}");
      if ($("library-setting-default-sort")) $("library-setting-default-sort").value = settings.defaultSort || "event_date";
      if ($("library-sort")) $("library-sort").value = settings.defaultSort || "event_date";
      if ($("library-setting-auto-refresh")) $("library-setting-auto-refresh").checked = settings.autoRefresh ?? true;
    } catch {}
  }

  function libraryAutoRefreshEnabled() {
    return $("library-setting-auto-refresh")?.checked ?? true;
  }

  return Object.freeze({
    addLibraryTag,
    applySavedLibrarySettings,
    fetchLibraryAnalytics,
    libraryAutoRefreshEnabled,
    persistLibrarySettings,
    removeLibraryTag,
    renderAnalyticsCharts,
    renderLibrarySummaryTiles,
    renderLibraryTags,
    renderPerformanceLibrary,
    renderPersonalBests,
    saveLibraryNotes,
  });
}
